"""Frozen-input detector comparison, no DB/API writes or live model changes."""
import sys, json, time, hashlib, argparse, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from PIL import Image
from crawler.storage.files import save_json
from Model.application.ai.CandidateObjectDetectorService import CandidateObjectDetectorService
from scripts.screen_shape_confusion import assess, overlay
from scripts.pairwise_image_search import detection_for_target, draw_detections


def qualifies(summary, errors):
    if errors:
        return False
    for cid, minimum in [('3',.8),('5',.9)]:
        s=summary['singles'][cid]
        if not s['count'] or s['correct']/s['count'] < minimum:
            return False
    for s in summary['pairs'].values():
        if not s['count'] or s['correct']/s['count'] < .75 or s['correct'] < s['paddingBaselineCorrect']:
            return False
    return True


def run(kind, device='cpu', prompt_style='baseline'):
    import torch
    torch.set_num_threads(4)
    out = ROOT/'data/detector_comparison'/f'{kind}_{time.strftime("%Y%m%d_%H%M%S")}'
    out.mkdir(parents=True, exist_ok=False); (out/'boxes').mkdir()
    singles = json.loads((ROOT/'data/screen_confusion_tests/report.json').read_text(encoding='utf-8'))
    pairs = json.loads((ROOT/'data/pairwise_search_tests/report.json').read_text(encoding='utf-8'))
    baseline = json.loads((ROOT/'data/detector_methods_1_2/report.json').read_text(encoding='utf-8'))
    detector = CandidateObjectDetectorService(kind, padding=kind=='owlv2', device=device, prompt_style=prompt_style)
    report = {'model':detector.MODELS[kind], 'kind':kind, 'device':device, 'padding':detector.padding, 'threshold':detector.threshold,
              'promptStyle':prompt_style, 'queries':list(detector.QUERY_STYLES[prompt_style]),
              'singleCases':[], 'pairedCases':[], 'errors':[], 'liveSettingsChanged':False,
              'qualityGate':{'tabletTop1Minimum':.8,'watchTop1Minimum':.9,'pairEachClassMinimum':.75,
                             'requireNoPairClassRegressionAgainstPadding':True,'requireNoInferenceErrors':True},
              'limits':['Product-region label correctness, not precise bounding-box IoU/mAP.',
                        'Previously observed development catalogue; 40 products include only 37 unique photos.',
                        'Pairs reuse one representative per category, not four independent products.',
                        'Different model confidence scales; fixed thresholds, no tuning on benchmark answers.',
                        'Grounding DINO uses phrase-token max confidence with threshold .4; processor preserves aspect ratio.',
                        'Only inference adapters change; no changes to retrieval or Gemini calls.']}
    save_json(out/'preregistered.json',report)
    t = time.perf_counter(); detector.load(); report['loadSeconds']=time.perf_counter()-t
    for i, old in enumerate(singles['cases'],1):
        path=ROOT/old['imagePath']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=old['sourceSHA256']: raise RuntimeError('Changed input')
        row={k:old[k] for k in ('articleID','categoryID','productName','imagePath','sourceSHA256','traits')}
        row['baseline']=old['original']['assessment']
        with Image.open(path) as photo: image=photo.convert('RGB')
        start=time.perf_counter()
        try: detections=detector.detectProducts(image)
        except Exception as exc:
            detections=[]; report['errors'].append({'input':row['articleID'],'error':repr(exc)})
        row.update(detections=detections,seconds=time.perf_counter()-start,
                   assessment=assess(detections,row['categoryID'],row['traits']['coarseProductROI']))
        row['overlay']=f'boxes/single_{row["articleID"]}.png'
        overlay(image,detections,row['traits']['coarseProductROI']).save(out/row['overlay'])
        report['singleCases'].append(row); save_json(out/'partial_results.json',report)
        print(f'{kind} single {i}/40 #{row["articleID"]}: class={row["assessment"]["predictedCategoryID"]}, {row["seconds"]:.2f}s',flush=True)
    for i, old in enumerate(pairs['pairs'],1):
        path=ROOT/'data/pairwise_search_tests'/old['queryImage']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=old['querySHA256']: raise RuntimeError('Changed pair input')
        with Image.open(path) as photo: image=photo.convert('RGB')
        start=time.perf_counter()
        try: detections=detector.detectProducts(image)
        except Exception as exc:
            detections=[]; report['errors'].append({'input':old['pairID'],'error':repr(exc)})
        targets=[]
        for target in old['targets']:
            top,correct=detection_for_target(detections,target)
            targets.append({'categoryID':target['categoryID'],'articleID':target['articleID'], 'top':top,
                            'isCorrect':bool(top and top['categoryID']==target['categoryID']),
                            'anyCorrect':correct is not None})
        row={'pairID':old['pairID'],'detections':detections,'targets':targets,'seconds':time.perf_counter()-start,
             'overlay':f'boxes/pair_{old["pairID"]}.png'}
        draw_detections(image,detections,[]).save(out/row['overlay']); report['pairedCases'].append(row)
        save_json(out/'partial_results.json',report)
        print(f'{kind} pair {i}/10 {old["pairID"]}: {sum(t["isCorrect"] for t in targets)}/2, {row["seconds"]:.2f}s',flush=True)
    summary={'singles':{},'pairs':{}}
    for cid in range(1,6):
        rows=[r for r in report['singleCases'] if r['categoryID']==cid]
        if rows:
            summary['singles'][str(cid)]={
                'count':len(rows),'correct':sum(r['assessment']['isCorrect'] for r in rows),
                'baselineCorrect':sum(r['baseline']['isCorrect'] for r in rows),
                'anyCorrect':sum(r['assessment']['anyCorrectProductBox'] for r in rows),
                'missed':sum(r['assessment']['missed'] for r in rows)}
        targets=[t for r in report['pairedCases'] for t in r['targets'] if t['categoryID']==cid]
        old_targets=[t for r in baseline['pairedCases'] for t in r['padding']['targets'] if t['categoryID']==cid]
        summary['pairs'][str(cid)]={'count':len(targets),'correct':sum(t['isCorrect'] for t in targets),
                                  'paddingBaselineCorrect':sum(t['isCorrect'] for t in old_targets),
                                  'anyCorrect':sum(t['anyCorrect'] for t in targets),
                                  'missed':sum(t['top'] is None for t in targets)}
    passed=qualifies(summary, report['errors'])
    report.update(summary=summary,qualityGatePassed=bool(passed),status='completed')
    report['inferenceSeconds']=sum(r['seconds'] for r in report['singleCases']+report['pairedCases'])
    save_json(out/'report.json',report)
    lines=['# Detector comparison','',f'Model: `{report["model"]}`. Quality gate passed: **{passed}**.','',
           '| Group | Category | Correct | Previous baseline | Any correct | Missed |','|---|---|---:|---:|---:|---:|']
    for group in ('singles','pairs'):
        for cid,s in summary[group].items():
            previous=s.get('baselineCorrect',s.get('paddingBaselineCorrect'))
            lines.append(f'| {group} | {cid} | {s["correct"]}/{s["count"]} | {previous}/{s["count"]} | {s["anyCorrect"]} | {s["missed"]} |')
    lines+=['']+['- '+x for x in report['limits']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    cards=''.join(f'<section><h3>{html.escape(str(r.get("articleID",r.get("pairID"))))}</h3><img src="{r["overlay"]}"></section>' for r in report['singleCases']+report['pairedCases'])
    (out/'index.html').write_text('<meta charset="utf-8"><style>body{font:16px system-ui}section{display:inline-block;width:30%;vertical-align:top}img{width:100%}pre{white-space:pre-wrap}</style><pre>'+html.escape('\n'.join(lines))+'</pre>'+cards,encoding='utf-8')
    print(json.dumps({'output':str(out),'qualityGatePassed':passed,'summary':summary,'inferenceSeconds':report['inferenceSeconds']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--kind',choices=['owlv2','grounding_dino'],default='owlv2')
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--prompt-style',choices=['baseline','concise'],default='baseline')
    args=parser.parse_args(); run(args.kind,args.device,args.prompt_style)

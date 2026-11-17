"""Read-only live API audit: count every returned box and check top labels per panel."""
import sys, json, hashlib, time, html, csv
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from scripts.pairwise_image_search import located_in_panel, overlap, draw_detections
from PIL import Image
import requests

NAMES={1:'Phone',2:'Laptop',3:'Tablet',4:'Headphones',5:'Watch'}


def iou(a,b):
    intersection=overlap(a,b)
    area_a=(a[2]-a[0])*(a[3]-a[1]); area_b=(b[2]-b[0])*(b[3]-b[1])
    union=area_a+area_b-intersection
    return intersection/union if union>0 else 0.


def analyze(detections,targets):
    boxes=[dict(d,boxIndex=i+1) for i,d in enumerate(detections)]
    groups=[]; assigned=set()
    for target in targets:
        local=sorted([d for d in boxes if located_in_panel(d,target['panelRegion'])],key=lambda d:-d['score'])
        assigned.update(d['boxIndex'] for d in local)
        top=local[0] if local else None
        correct=[d for d in local if d['categoryID']==target['categoryID']]
        intersections=[{'boxA':a['boxIndex'],'boxB':b['boxIndex'],'iou':iou(a['region'],b['region']),
                        'sameLabel':a['categoryID']==b['categoryID']}
                       for i,a in enumerate(local) for b in local[i+1:] if iou(a['region'],b['region'])>=.5]
        groups.append({'articleID':target['articleID'],'expectedCategoryID':target['categoryID'],
                       'boxCount':len(local),'boxes':local,'top':top,
                       'topCorrect':bool(top and top['categoryID']==target['categoryID']),
                       'correctBoxCount':len(correct),'bestCorrect':correct[0] if correct else None,
                       'overlappingBoxPairsIoU50':intersections})
    highest=max(boxes,key=lambda d:d['score'],default=None)
    expected=[t['categoryID'] for t in targets if highest and located_in_panel(highest,t['panelRegion'])]
    return {'totalBoxes':len(boxes),'targets':groups,'unassignedBoxes':[d for d in boxes if d['boxIndex'] not in assigned],
            'highestInImage':highest,'highestInImageCorrect':bool(highest and highest['categoryID'] in expected)}


def top_text(target):
    top=target['top']
    if not top:return f'{NAMES[target["expectedCategoryID"]]}: 0 box; MISSED'
    return f'{NAMES[target["expectedCategoryID"]]}: {target["boxCount"]} box; #{top["boxIndex"]} {NAMES[top["categoryID"]]} {top["score"]:.4f}; '+('Đúng' if target['topCorrect'] else 'Sai')


def main():
    source=ROOT/'data/pairwise_search_tests'
    original=json.loads((source/'report.json').read_text(encoding='utf-8'))
    out=ROOT/'data/detector_box_audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False); (out/'boxes').mkdir()
    session=requests.Session(); health=session.get('http://127.0.0.1:8008/api/health',timeout=20)
    health.raise_for_status(); state=health.json()
    assert state['detectorProvider']=='owlv2' and state['detectorPadding'] is True,'Unexpected active detector'
    report={'provider':state['detectorProvider'],'padding':state['detectorPadding'],'device':state['detectorDevice'],
            'labelPolicy':state.get('detectorLabelPolicy','raw'),
            'threshold':.15,'maxReturnedBoxes':12,'nmsApplied':False,'source':'Live POST /api/search/detect',
            'cases':[],'limits':['Counts refer to boxes returned by the active API: confidence > 0.15 and at most 12 per image, before any NMS.',
                               'Each expected product is identified using its panel: box center inside panel and at least 80% of box area inside panel.',
                               'Correct means correct category for that panel, not precise IoU against a manually labelled object box.',
                               'Ten pairs reuse five source products; 20 target occurrences are not 20 distinct products.',
                               'An overlapping pair with IoU >= 0.5 is a duplicate candidate, not proof: headphones may contain separate earbuds/case.',
                               'Scores are uncalibrated detector confidence, not probabilities of being correct. No detector settings or ranking changes.',
                               'If labelPolicy=provided_catalogue, counts refer to label-guided retained boxes with transform recovery, not unfiltered detector output.']}
    for index,pair in enumerate(original['pairs'],1):
        path=source/pair['queryImage']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==pair['querySHA256'],'Changed input'
        start=time.perf_counter()
        with path.open('rb') as f:
            response=session.post('http://127.0.0.1:8008/api/search/detect',files={'file':(path.name,f,'image/png')},timeout=180)
        response.raise_for_status(); body=response.json()
        if body.get('warnings'):raise RuntimeError(body['warnings'])
        row={'pairID':pair['pairID'],'inputImage':str(path.relative_to(ROOT)), 'inputSHA256':pair['querySHA256'],
             'seconds':time.perf_counter()-start, 'rawResponse':body, **analyze(body['regions'],pair['targets'])}
        row['overlay']=f'boxes/{pair["pairID"]}.png'
        with Image.open(path) as photo:draw_detections(photo.convert('RGB'),body['regions'],[]).save(out/row['overlay'])
        report['cases'].append(row); save_json(out/'partial_results.json',report)
        print(f'{index}/10 {row["pairID"]}: {row["totalBoxes"]} boxes; '+ ' | '.join(top_text(t) for t in row['targets']),flush=True)
    targets=[t for r in report['cases'] for t in r['targets']]
    report['summary']={'images':len(report['cases']),'totalBoxes':sum(r['totalBoxes'] for r in report['cases']),
                       'targets':len(targets),'correctTopPerTarget':sum(t['topCorrect'] for t in targets),
                       'targetsWithMultipleBoxes':sum(t['boxCount']>1 for t in targets),
                       'targetsWithAnyCorrectBox':sum(t['correctBoxCount']>0 for t in targets),
                       'imagesWithCorrectGlobalTop':sum(r['highestInImageCorrect'] for r in report['cases']),
                       'unassignedBoxes':sum(len(r['unassignedBoxes']) for r in report['cases']),
                       'overlappingBoxPairsIoU50':sum(len(t['overlappingBoxPairsIoU50']) for t in targets)}
    save_json(out/'report.json',report)
    lines=['# Khảo sát bounding box OWLv2 + padding','',
           '| Ảnh ghép | Tổng box | Sản phẩm trái: số box và box điểm cao nhất | Sản phẩm phải: số box và box điểm cao nhất | Box ngoài hai vùng |',
           '|---|---:|---|---|---:|']
    for row in report['cases']:
        lines.append(f'| {row["pairID"]} | {row["totalBoxes"]} | {top_text(row["targets"][0])} | {top_text(row["targets"][1])} | {len(row["unassignedBoxes"])} |')
    lines+=['','## Tổng hợp','',json.dumps(report['summary'],indent=2),'','## Giới hạn','']+['- '+s for s in report['limits']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    with (out/'boxes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f); writer.writerow(['pair','expectedCategory','boxIndex','predictedCategory','confidence','topInPanel','correctLabel','x1','y1','x2','y2'])
        for row in report['cases']:
            for target in row['targets']:
                for box in target['boxes']:
                    writer.writerow([row['pairID'],NAMES[target['expectedCategoryID']],box['boxIndex'],NAMES[box['categoryID']],box['score'],box==target['top'],box['categoryID']==target['expectedCategoryID'],*box['region']])
    cards=[]
    for row in report['cases']:
        details=[]
        for target in row['targets']:
            details.append('<h3>'+html.escape(top_text(target))+'</h3><table><tr><th>Box</th><th>Nhãn</th><th>Điểm</th><th>Đúng nhãn</th></tr>'+''.join(f'<tr><td>#{d["boxIndex"]}</td><td>{NAMES[d["categoryID"]]}</td><td>{d["score"]:.6f}</td><td>{d["categoryID"]==target["expectedCategoryID"]}</td></tr>' for d in target['boxes'])+'</table>')
        cards.append(f'<article><h2>{row["pairID"]}: {row["totalBoxes"]} boxes</h2><img src="{row["overlay"]}">'+''.join(details)+'</article>')
    (out/'index.html').write_text('<meta charset="utf-8"><title>OWLv2 box audit</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto}img{width:100%}article{border:1px solid #ccc;padding:15px;margin:20px 0}td,th{border:1px solid #ccc;padding:6px}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>OWLv2 + padding: 10 ảnh ghép</h1><pre>'+html.escape('\n'.join(lines))+'</pre>'+''.join(cards),encoding='utf-8')
    print(json.dumps({'output':str(out),'summary':report['summary']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()

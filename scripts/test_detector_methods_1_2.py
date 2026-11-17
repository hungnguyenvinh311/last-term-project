"""Fixed factorial experiment: baseline/padding/descriptive prompts/both, no deployment."""
import sys,json,os,time,hashlib,html
from pathlib import Path
from collections import Counter
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.ai.detection_categories import DETECTION_LABELS
from scripts.screen_shape_confusion import assess,overlay
from scripts.pairwise_image_search import detection_for_target,draw_detections
from scripts.pair_letterbox_audit import pad_square

# Three positive descriptions per class. Fixed before this experiment, not selected
# using results. Raw prompt labels map to the same five catalogue categories.
PROMPT_BANK={
 1:['a mobile phone','a smartphone','a handheld cellular telephone'],
 2:['a laptop computer','an open notebook computer with a keyboard','a portable laptop with a screen and keyboard'],
 3:['a tablet computer','a touchscreen tablet device','an iPad or Android tablet computer'],
 4:['headphones','wireless earbuds in a charging case','a pair of earphones'],
 5:['a smartwatch','a wristwatch with a strap','a digital watch worn on the wrist'],
}
CONDITIONS={'baseline':(False,False),'padding':(True,False),'prompts':(False,True),'combined':(True,True)}

def flatten_bank(bank):
    if set(bank)!={1,2,3,4,5} or len({len(v) for v in bank.values()})!=1:raise ValueError('Equal prompt counts for all five categories required')
    labels=[];categories=[]
    for cid in range(1,6):
        for label in bank[cid]:
            if not label.strip():raise ValueError('Empty prompt')
            labels.append(label);categories.append(cid)
    return labels,categories

def unpad(region,size,query_size,offset):
    w,h=size;qw,qh=query_size;left,top=offset
    r=[(region[0]*qw-left)/w,(region[1]*qh-top)/h,(region[2]*qw-left)/w,(region[3]*qh-top)/h]
    r=[max(0.,min(1.,v)) for v in r]
    return r if r[2]>r[0] and r[3]>r[1] else None

def pixel_key(image,bank):return (hashlib.sha256(image.tobytes()+str(image.size).encode()).hexdigest(),bank)

class ExperimentDetector:
    def __init__(self):self.adapter=ObjectDetectorService();self.cache={};self.calls=0
    def raw(self,query,enhanced):
        bank='descriptive' if enhanced else 'baseline';key=pixel_key(query,bank)
        if key in self.cache:return deepcopy(self.cache[key]),True
        if self.adapter.model is None:
            initial=self.adapter.detectProducts(query)
            self.cache[pixel_key(query,'baseline')]=deepcopy(initial)
            self.calls+=1
            if not enhanced:return initial,False
        if enhanced:labels,categories=flatten_bank(PROMPT_BANK)
        else:labels=list(DETECTION_LABELS);categories=list(range(1,6))
        import torch
        inputs=self.adapter.processor(text=[labels],images=query,return_tensors='pt')
        with torch.inference_mode():outputs=self.adapter.model(**inputs)
        result=self.adapter.processor.post_process_object_detection(outputs=outputs,target_sizes=torch.tensor([[query.height,query.width]]),threshold=.15)[0]
        detections=[]
        for box,label,score in zip(result['boxes'],result['labels'],result['scores']):
            i=int(label);cid=categories[i];x1,y1,x2,y2=box.tolist()
            detections.append({'label':DETECTION_LABELS[cid-1],'categoryID':cid,'matchedPrompt':labels[i],'score':float(score),
                               'region':[max(0,x1/query.width),max(0,y1/query.height),min(1,x2/query.width),min(1,y2/query.height)]})
        detections=sorted(detections,key=lambda d:-d['score'])[:12]
        self.cache[key]=deepcopy(detections);self.calls+=1
        return detections,False
    def detect(self,image,padding,enhanced):
        query,offset=pad_square(image) if padding else (image,(0,0))
        raw,cached=self.raw(query,enhanced);mapped=[]
        for d in raw:
            region=unpad(d['region'],image.size,query.size,offset)
            if region is not None:mapped.append({**d,'region':region})
        return {'detections':mapped,'rawQueryDetections':raw,'querySize':list(query.size),'paddingOffset':list(offset),'cacheHit':cached}

def category_metrics(rows,condition,cid,pairs=False,dedup=False):
    if pairs:
        values=[t for row in rows for t in row[condition]['targets'] if t['categoryID']==cid]
        correct=sum(v['isCorrect'] for v in values);available=sum(v['correctAvailable'] for v in values)
        missed=sum(v['top'] is None for v in values);phone=sum(bool(v['top'] and v['top']['categoryID']==1) for v in values)
    else:
        values=[r for r in rows if r['categoryID']==cid]
        if dedup:values=list({r['sourceSHA256']:r for r in values}.values())
        a=[r[condition]['assessment'] for r in values]
        correct=sum(v['isCorrect'] for v in a);available=sum(v['anyCorrectProductBox'] for v in a);missed=sum(v['missed'] for v in a);phone=sum(v['isPhone'] for v in a)
    n=len(values)
    return {'count':n,'correctTop1':correct,'correctTop1Rate':correct/n if n else None,
            'correctLabelAvailable':available,'missed':missed,'phoneTop1':phone}

def render(out,report):
    table=['| Input | Condition | Tablet correct top1 | Watch correct top1 |','|---|---|---:|---:|']
    for scope in ('singleImages','pairedImages'):
        for condition,values in report['summary'][scope].items():
            a=values['tablet'];b=values['watch']
            table.append(f'| {scope} | {condition} | {a["correctTop1"]}/{a["count"]} ({a["correctTop1Rate"]*100:.1f}%) | {b["correctTop1"]}/{b["count"]} ({b["correctTop1Rate"]*100:.1f}%) |')
    (out/'report.md').write_text('# Fixed detector-method comparison\n\n'+'\n'.join(table)+'\n\n'+'\n'.join('- '+v for v in report['limits'])+'\n',encoding='utf-8')
    cards=[]
    for row in report['singleCases']:
        parts=[]
        for condition in CONDITIONS:
            a=row[condition]['assessment'];parts.append(f'<section><b>{condition}: class {a["predictedCategoryID"]}, correct={a["isCorrect"]}</b><img src="{row[condition]["overlay"]}"></section>')
        cards.append(f'<article><h3>#{row["articleID"]} {html.escape(row["productName"])}</h3><div>'+''.join(parts)+'</div></article>')
    for row in report['pairedCases']:
        cards.append(f'<article><h3>{row["pairID"]}</h3><div>'+''.join(f'<section><b>{condition}</b><img src="{row[condition]["overlay"]}"></section>' for condition in CONDITIONS)+'</div></article>')
    head='<!doctype html><meta charset="utf-8"><title>Detector methods 1+2</title><style>body{font:14px system-ui;max-width:1500px;margin:25px auto}article{border:1px solid #ddd;padding:12px;margin:20px 0}article div{display:flex;gap:8px}section{width:25%}img{width:100%;height:auto}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}</style><h1>Padding và mô tả nhãn — thử nghiệm 4 cấu hình</h1><p>Đúng loại trong vùng sản phẩm thô; chưa phải mAP/IoU chuẩn. Baseline, chỉ padding, chỉ đổi prompt, kết hợp cả hai. Ảnh đơn: 20 tablet + 20 watch; ảnh ghép: mỗi nhóm có 4 lượt.</p>'
    summary='<table><tr><th>Input</th><th>Condition</th><th>Tablet</th><th>Watch</th></tr>'
    for scope,conditions in report['summary'].items():
        if scope=='uniqueSingleImages':continue
        for name,v in conditions.items():
            a=v['tablet'];b=v['watch'];summary+=f'<tr><td>{scope}</td><td>{name}</td><td>{a["correctTop1"]}/{a["count"]}</td><td>{b["correctTop1"]}/{b["count"]}</td></tr>'
    (out/'index.html').write_text(head+summary+'</table>'+''.join(cards),encoding='utf-8')

def main():
    out=ROOT/'data/detector_methods_1_2';out.mkdir(exist_ok=False)
    (out/'single_boxes').mkdir();(out/'pair_boxes').mkdir()
    previous=json.loads((ROOT/'data/screen_confusion_tests/report.json').read_text(encoding='utf-8'))
    paired=json.loads((ROOT/'data/pairwise_search_tests/report.json').read_text(encoding='utf-8'))
    current_code=hashlib.sha256((ROOT/'Model/application/ai/ObjectDetectorService.py').read_bytes()).hexdigest()
    if previous['detectorCodeSHA256']!=current_code:raise RuntimeError('Baseline adapter changed; do not reuse previous results')
    if previous['model']!=os.getenv('APP_DETECTOR_MODEL','google/owlvit-base-patch32') or previous['prompts']!=list(DETECTION_LABELS) or previous['threshold']!=.15:raise RuntimeError('Baseline settings differ')
    save_json(out/'preregistered_conditions.json',{'conditions':CONDITIONS,'prompts':PROMPT_BANK,'threshold':.15,'selection':'Fixed bank, no prompt/threshold grid or changes after observing outcomes','baselineArtifact':'data/screen_confusion_tests/report.json'})
    os.environ.setdefault('HF_HUB_OFFLINE','1');detector=ExperimentDetector();start=time.perf_counter()
    report={'model':previous['model'],'conditions':CONDITIONS,'promptBank':PROMPT_BANK,'threshold':.15,
            'singleCases':[],'pairedCases':[],'liveSettingsChanged':False,
            'limits':['Correct means highest-confidence product-region box has the expected category under the previously frozen coarse-ROI rule, not object-box IoU/mAP.',
                      'All 40 single source photos are square; padding alone should not change them. Tablet duplicates are also reported separately.',
                      'Paired benchmark has one catalogue representative per class, only four tablet and four watch targets.',
                      'Prompts are a fixed balanced three-per-class bank; max-scoring prompt maps to its category. No result-driven edits or class-specific threshold tuning.',
                      'Same development catalogue and previously observed images; no independent generalization claim.',
                      'Prompt scores are uncalibrated confidences, not correctness probabilities. Correct-label availability is reported separately from top1.',
                      'The baseline single-image detections are reused only after checking unchanged adapter source hash, model, prompts, threshold and source image SHA.',
                      'No Gemini calls, new models, database writes or live detector configuration changes.']}
    for index,old in enumerate(previous['cases'],1):
        path=ROOT/old['imagePath'];content=path.read_bytes()
        if hashlib.sha256(content).hexdigest()!=old['sourceSHA256']:raise RuntimeError('Source image changed')
        with Image.open(path) as p:image=p.convert('RGB')
        detector.cache[pixel_key(image,'baseline')]=deepcopy(old['original']['detections'])
        row={k:deepcopy(old[k]) for k in ('articleID','categoryID','productName','imagePath','sourceSHA256','traits')}
        for name,(padding,enhanced) in CONDITIONS.items():
            result=detector.detect(image,padding,enhanced)
            result['assessment']=assess(result['detections'],row['categoryID'],row['traits']['coarseProductROI'])
            file=f'single_boxes/{row["articleID"]}_{name}.png';overlay(image,result['detections'],row['traits']['coarseProductROI']).save(out/file);result['overlay']=file
            row[name]=result
        report['singleCases'].append(row);save_json(out/'partial_results.json',report)
        print(f'{index}/40 ID {row["articleID"]}: '+', '.join(f'{name}={row[name]["assessment"]["predictedCategoryID"]}' for name in CONDITIONS),flush=True)
    for index,old in enumerate(paired['pairs'],1):
        path=ROOT/'data/pairwise_search_tests'/old['queryImage']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=old['querySHA256']:raise RuntimeError('Pair input changed')
        with Image.open(path) as p:image=p.convert('RGB')
        row={'pairID':old['pairID']}
        for name,(padding,enhanced) in CONDITIONS.items():
            result=detector.detect(image,padding,enhanced);targets=[]
            for target in old['targets']:
                top,correct=detection_for_target(result['detections'],target)
                targets.append({'articleID':target['articleID'],'categoryID':target['categoryID'],'top':top,
                                'isCorrect':bool(top and top['categoryID']==target['categoryID']),'correctAvailable':correct is not None})
            result['targets']=targets;file=f'pair_boxes/{old["pairID"]}_{name}.png';draw_detections(image,result['detections'],[]).save(out/file);result['overlay']=file
            row[name]=result
        report['pairedCases'].append(row);save_json(out/'partial_results.json',report)
        print(f'pair {index}/10 {old["pairID"]}: '+', '.join(f'{name}={sum(t["isCorrect"] for t in row[name]["targets"])}' for name in CONDITIONS),flush=True)
    report['summary']={scope:{condition:{label:category_metrics(rows,condition,cid,pairs=scope=='pairedImages',dedup=scope=='uniqueSingleImages') for label,cid in [('tablet',3),('watch',5)]} for condition in CONDITIONS} for scope,rows in [('singleImages',report['singleCases']),('uniqueSingleImages',report['singleCases']),('pairedImages',report['pairedCases'])]}
    report['newInferenceCalls']=detector.calls;report['seconds']=time.perf_counter()-start;report['status']='completed_fixed_comparison'
    save_json(out/'report.json',report);render(out,report)
    print(json.dumps(report['summary'],ensure_ascii=False),flush=True)

if __name__=='__main__':main()

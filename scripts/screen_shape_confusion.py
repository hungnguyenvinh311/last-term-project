"""Audit all catalogue tablets/watches with unchanged detector, plus grayscale control."""
import sys,json,os,time,hashlib,html,math,argparse
from pathlib import Path
from copy import deepcopy
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageOps,ImageDraw,ImageFont
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.ai.detection_categories import DETECTION_LABELS

# Visual traits recorded before inference, from the catalogue contact sheets.
RECTANGULAR_WATCHES={81,89,95,99,101,102,103,106,107}
COLOURFUL_WATCH_UI={81,82,88,89,95,99,101,102,107}
PROMOTIONAL_WATCH_PHOTOS={81,82,83,84,86,88,89,91,92,93,94}

def traits(product):
    cid=product['categoryID'];articleID=product['articleID']
    if cid not in (3,5):raise ValueError('Only tablets and watches are in this audit')
    shape='rectangular' if cid==3 or articleID in RECTANGULAR_WATCHES else 'round'
    ui='colourful_ui' if cid==3 or articleID in COLOURFUL_WATCH_UI else 'dark_ui_coloured_accents'
    roi=[.02,.13,.65,.94] if cid==5 and articleID in PROMOTIONAL_WATCH_PHOTOS else [.02,.02,.98,.98]
    return {'shape':shape,'screenAppearance':ui,'coarseProductROI':roi,
            'annotationMethod':'assistant visual inspection; coarse ROI, not exact object ground-truth box',
            'hypothesisSubset':shape=='rectangular' and ui=='colourful_ui'}

def box_area(r):return max(0,r[2]-r[0])*max(0,r[3]-r[1])

def plausible_product_box(detection,roi):
    r=detection.get('region')
    if not isinstance(r,list) or len(r)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in r):return False
    area=box_area(r);expected=box_area(roi)
    if area<=0 or area<.05*expected:return False
    cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
    intersection=max(0,min(r[2],roi[2])-max(r[0],roi[0]))*max(0,min(r[3],roi[3])-max(r[1],roi[1]))
    return roi[0]<=cx<=roi[2] and roi[1]<=cy<=roi[3] and intersection/area>=.7

def assess(detections,category,roi):
    local=[dict(d,index=i+1) for i,d in enumerate(detections) if plausible_product_box(d,roi)]
    top=max(local,key=lambda d:d['score'],default=None)
    raw_top=max(detections,key=lambda d:d['score'],default=None)
    return {'strongestProductDetection':top,'strongestAnywhere':raw_top,
            'predictedCategoryID':top['categoryID'] if top else None,
            'isPhone':bool(top and top['categoryID']==1),'isCorrect':bool(top and top['categoryID']==category),
            'anyPhoneProductBox':any(d['categoryID']==1 for d in local),
            'anyCorrectProductBox':any(d['categoryID']==category for d in local),
            'missed':not local,'retainedProductBoxes':len(local)}

def summarize(rows,variant,deduplicate=False):
    if deduplicate:
        unique={}
        for row in rows:unique.setdefault(row['sourceSHA256'],row)
        rows=list(unique.values())
    n=len(rows);a=[row[variant]['assessment'] for row in rows]
    return {'images':n,'phoneTop1':sum(v['isPhone'] for v in a),
            'phoneTop1Rate':sum(v['isPhone'] for v in a)/n if n else None,
            'phoneAnyBox':sum(v['anyPhoneProductBox'] for v in a),
            'phoneAnyBoxRate':sum(v['anyPhoneProductBox'] for v in a)/n if n else None,
            'rawPhoneAnyBox':sum(any(d['categoryID']==1 for d in row[variant].get('detections',[])) for row in rows),
            'rawPhoneTop1':sum(bool(v['strongestAnywhere'] and v['strongestAnywhere']['categoryID']==1) for v in a),
            'correctTop1':sum(v['isCorrect'] for v in a),'correctAnyBox':sum(v['anyCorrectProductBox'] for v in a),
            'missed':sum(v['missed'] for v in a),
            'predictedCategoryCounts':dict(Counter(str(v['predictedCategoryID']) for v in a))}

def grouped_summary(rows):
    groups={'all40':rows,'tablets':[r for r in rows if r['categoryID']==3],
            'watches':[r for r in rows if r['categoryID']==5],
            'rectangularWatches':[r for r in rows if r['categoryID']==5 and r['traits']['shape']=='rectangular'],
            'roundWatches':[r for r in rows if r['categoryID']==5 and r['traits']['shape']=='round'],
            'rectangularColourful':[r for r in rows if r['traits']['hypothesisSubset']],
            'rectangularColourfulWatches':[r for r in rows if r['categoryID']==5 and r['traits']['hypothesisSubset']]}
    return {name:{variant:{'productWeighted':summarize(items,variant),'uniqueSourceImages':summarize(items,variant,True)} for variant in ('original','grayscale')} for name,items in groups.items()}

def overlay(image,detections,roi):
    result=ImageOps.contain(image.copy(),(900,900));draw=ImageDraw.Draw(result);w,h=result.size
    draw.rectangle([roi[0]*w,roi[1]*h,roi[2]*w,roi[3]*h],outline='#007c68',width=2)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    for i,d in enumerate(detections):
        r=d['region']
        if box_area(r)<=0:continue
        box=[r[0]*w,r[1]*h,r[2]*w,r[3]*h];colour='#c43816' if d['categoryID']==1 else '#254dcb'
        draw.rectangle(box,outline=colour,width=2)
        label=f'{i+1}. {d["label"]} {d["score"]:.3f}'
        x=max(0,box[0]);y=max(0,box[1]-18);bounds=draw.textbbox((x,y),label,font=font)
        draw.rectangle(bounds,fill='white');draw.text((x,y),label,fill=colour,font=font)
    return result

def render(out,report):
    lines=['# Tablet/watch screen-confusion audit','',
           '| Group | Products | Phone top1 original | Phone top1 grayscale | Any phone box original | Correct top1 original | Missed original |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for name,g in report['groups'].items():
        a=g['original']['productWeighted'];b=g['grayscale']['productWeighted']
        lines.append(f'| {name} | {a["images"]} | {a["phoneTop1"]} ({100*a["phoneTop1Rate"]:.1f}%) | {b["phoneTop1"]} ({100*b["phoneTop1Rate"]:.1f}%) | {a["phoneAnyBox"]} | {a["correctTop1"]} | {a["missed"]} |')
    lines+=['','## Method and limits','']+['- '+v for v in report['limits']]
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    cards=[]
    for r in report['cases']:
        a=r['original']['assessment'];b=r['grayscale']['assessment']
        cards.append(f'<article><h3>#{r["articleID"]} {html.escape(r["productName"])}</h3><p>{r["traits"]["shape"]} · {r["traits"]["screenAppearance"]}</p><p>Nhãn mạnh nhất vùng sản phẩm: ảnh gốc {a["predictedCategoryID"]}, ảnh xám {b["predictedCategoryID"]}. 1=phone, 2=laptop, 3=tablet, 4=headphones, 5=watch, None=không có khung hợp lệ.</p><div><img src="{r["original"]["overlay"]}"><img src="{r["grayscale"]["overlay"]}"></div></article>')
    summary='<table><tr><th>Nhóm</th><th>N</th><th>Ảnh gốc → phone</th><th>Ảnh xám → phone</th><th>Ảnh gốc đúng loại</th></tr>'
    for name,g in report['groups'].items():
        a=g['original']['productWeighted'];b=g['grayscale']['productWeighted']
        summary+=f'<tr><td>{name}</td><td>{a["images"]}</td><td>{a["phoneTop1"]} ({100*a["phoneTop1Rate"]:.1f}%)</td><td>{b["phoneTop1"]} ({100*b["phoneTop1Rate"]:.1f}%)</td><td>{a["correctTop1"]}</td></tr>'
    summary+='</table>'
    page='<!doctype html><meta charset="utf-8"><title>Tablet/watch confusion audit</title><style>body{font:15px system-ui;max-width:1200px;margin:30px auto}article{border:1px solid #ddd;margin:20px 0;padding:16px}article div{display:flex}img{width:50%;object-fit:contain}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}</style><h1>Kiểm tra 20 tablet và 20 đồng hồ</h1><p>Giữ nguyên model, 5 prompt và ngưỡng 0,15. Khung đỏ: mobile phone; khung xanh dương: các lớp khác; khung xanh lá: vùng sản phẩm thô dùng đối chiếu. Nhãn trong bảng là khung phù hợp vùng sản phẩm có confidence cao nhất. Xem report.json để phân biệt có nhãn phone bất kỳ và phone mạnh nhất.</p>'
    (out/'index.html').write_text(page+summary+''.join(cards),encoding='utf-8')

def run(output):
    output=Path(output).resolve();output.relative_to((ROOT/'data').resolve())
    if output.exists():raise RuntimeError('Output exists; use another directory to preserve results')
    rows=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    products=sorted([p for p in rows if p['categoryID'] in (3,5)],key=lambda p:p['articleID'])
    if Counter(p['categoryID'] for p in products)!={3:20,5:20}:raise ValueError('Expected 20 tablets and 20 watches')
    output.mkdir(parents=True,exist_ok=False)
    for folder in ('images/original','images/grayscale','boxes/original','boxes/grayscale'):(output/folder).mkdir(parents=True)
    annotations=[{'articleID':p['articleID'],**traits(p)} for p in products]
    save_json(output/'visual_traits_before_inference.json',annotations)
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    detector=ObjectDetectorService();cache={};start=time.perf_counter()
    report={'model':os.getenv('APP_DETECTOR_MODEL','google/owlvit-base-patch32'),'threshold':.15,
            'prompts':list(DETECTION_LABELS),'detectorCodeSHA256':hashlib.sha256((ROOT/'Model/application/ai/ObjectDetectorService.py').read_bytes()).hexdigest(),
            'roiPolicy':'Coarse product ROI from visual inspection before inference. Candidate centre inside ROI, >=70% detection area inside ROI, detection area >=5% ROI. Raw predictions retained.',
            'limits':['All 40 catalogue records are included; repeated image bytes are counted separately and also reported deduplicated.',
                      'Shapes/screen appearance/coarse ROIs are assistant visual observations, not manufacturer ground truth or precise object boxes.',
                      'Phone top1 means the highest-confidence retained product-region box is phone. Any-phone-box rate is a different, separately reported measure.',
                      'Boxes outside the coarse ROI or below 5% ROI area are excluded only from the product assessment, not deleted from raw predictions.',
                      'Grayscale is an input ablation on the same image, not a production fix. Differences do not isolate screen colour from every other coloured region.',
                      'Original images retain advertising, accessories and scene layout. Association with shape/colour does not prove which internal features the model uses.',
                      'No API provider calls, catalogue/database changes, retrieval reweighting, detector prompt/threshold tuning or model downloads were requested.'],
            'cases':[]}
    for n,p in enumerate(products,1):
        content=(ROOT/p['imagePath']).read_bytes()
        with Image.open(ROOT/p['imagePath']) as original:image=original.convert('RGB')
        row={k:p[k] for k in ('articleID','categoryID','productName','imagePath')};row['sourceSHA256']=hashlib.sha256(content).hexdigest();row['traits']=traits(p)
        for variant,photo in [('original',image),('grayscale',ImageOps.grayscale(image).convert('RGB'))]:
            image_path=f'images/{variant}/{p["articleID"]}.png';photo.save(output/image_path)
            digest=hashlib.sha256(photo.tobytes()+str(photo.size).encode()).hexdigest()
            started=time.perf_counter();error=None
            if digest not in cache:
                try:cache[digest]=detector.detectProducts(photo)
                except Exception as exc:error=type(exc).__name__
            detections=deepcopy(cache.get(digest,[]))
            overlay_path=f'boxes/{variant}/{p["articleID"]}.png';overlay(photo,detections,row['traits']['coarseProductROI']).save(output/overlay_path)
            row[variant]={'image':image_path,'overlay':overlay_path,'detections':detections,'assessment':assess(detections,p['categoryID'],row['traits']['coarseProductROI']),
                          'error':error,'seconds':time.perf_counter()-started}
        report['cases'].append(row);save_json(output/'partial_results.json',report)
        a=row['original']['assessment'];b=row['grayscale']['assessment']
        print(f'{n}/40 ID {p["articleID"]}: expected={p["categoryID"]}, original={a["predictedCategoryID"]}, grayscale={b["predictedCategoryID"]}',flush=True)
    report['groups']=grouped_summary(report['cases'])
    report['transitions']={'originalPhoneToGrayCorrect':[r['articleID'] for r in report['cases'] if r['original']['assessment']['isPhone'] and r['grayscale']['assessment']['isCorrect']],
                           'originalPhoneStillGrayPhone':[r['articleID'] for r in report['cases'] if r['original']['assessment']['isPhone'] and r['grayscale']['assessment']['isPhone']]}
    report['seconds']=time.perf_counter()-start;report['uniqueInferenceInputs']=len(cache)
    report['status']='completed_observational_experiment'
    save_json(output/'report.json',report);render(output,report)
    print(json.dumps(report['groups'],ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'data/screen_confusion_tests'))
    run(parser.parse_args().output)

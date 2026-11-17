"""Fixed six-view audit of the seven previously failed product photographs."""
import sys,json,hashlib,time,html,io,csv
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from scripts.screen_shape_confusion import assess,overlay,plausible_product_box
from PIL import Image,ImageOps
import requests

VARIANTS=('original','rotate90cw','rotate180','rotate270cw','flip_horizontal','flip_vertical')
LABELS={'original':'Gốc','rotate90cw':'Xoay 90°','rotate180':'Xoay 180°','rotate270cw':'Xoay 270°',
        'flip_horizontal':'Lật ngang','flip_vertical':'Lật dọc'}
NAMES={1:'Phone',2:'Laptop',3:'Tablet',4:'Headphones',5:'Watch',None:'MISSED'}


def transform(image,roi,variant):
    x1,y1,x2,y2=roi
    if variant=='original':return image.copy(),list(roi)
    operations={
        'rotate90cw':(Image.Transpose.ROTATE_270,[1-y2,x1,1-y1,x2]),
        'rotate180':(Image.Transpose.ROTATE_180,[1-x2,1-y2,1-x1,1-y1]),
        'rotate270cw':(Image.Transpose.ROTATE_90,[y1,1-x2,y2,1-x1]),
        'flip_horizontal':(Image.Transpose.FLIP_LEFT_RIGHT,[1-x2,y1,1-x1,y2]),
        'flip_vertical':(Image.Transpose.FLIP_TOP_BOTTOM,[x1,1-y2,x2,1-y1])}
    operation,region=operations[variant]
    return image.transpose(operation),region


def main():
    source=ROOT/'data/detector_single_box_audit/20261104T150354Z/report.json'
    previous=json.loads(source.read_text(encoding='utf-8'))
    failed=[r for r in previous['cases'] if not r['original']['assessment']['anyCorrectProductBox']]
    assert {r['articleID'] for r in failed}=={42,43,49,50,57,58,95},'Unexpected source failures'
    out=ROOT/'data/detector_transform_audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False); (out/'images').mkdir(); (out/'boxes').mkdir()
    client=requests.Session(); response=client.get('http://127.0.0.1:8008/api/health',timeout=20)
    response.raise_for_status(); health=response.json()
    assert health['detectorProvider']=='owlv2' and health['detectorPadding'] is True,'Unexpected active detector'
    report={'provider':'owlv2','padding':True,'device':health['detectorDevice'],'threshold':.15,'maxReturnedBoxes':12,
            'variants':VARIANTS,'rotationConvention':'Clockwise; exact transpose, no interpolation',
            'sourceAudit':str(source.relative_to(ROOT)), 'cases':[], 'errors':[],
            'limits':['Seven previously failed development images, not a random or held-out sample.',
                      'Six fixed views: unchanged decoded pixels, clockwise 90/180/270 degrees, horizontal and vertical reflection. PNG encoding avoids additional JPEG loss.',
                      'Product ROI is transformed together with the image and used only for assessment, never provided to the detector.',
                      'Success means at least one returned correctly labelled box in the product ROI, not exact object IoU/mAP or a correct highest-score box.',
                      'Threshold .15 and top 12 are unchanged; no NMS, per-image prompt changes or production transform aggregation.',
                      'Increased success after trying several views is measured on selected failures and does not establish overall accuracy.']}
    save_json(out/'preregistered.json',report)
    for product in failed:
        path=ROOT/product['imagePath']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==product['sourceSHA256'],'Source image changed'
        with Image.open(path) as photo:image=photo.convert('RGB')
        row={k:product[k] for k in ('articleID','categoryID','productName','imagePath','sourceSHA256')}
        row['variants']={}
        for variant in VARIANTS:
            query,roi=transform(image,product['traits']['coarseProductROI'],variant)
            image_path=f'images/{row["articleID"]}_{variant}.png'; query.save(out/image_path)
            content=(out/image_path).read_bytes(); start=time.perf_counter()
            result={'image':image_path,'inputSHA256':hashlib.sha256(content).hexdigest(),'roi':roi,'status':'completed'}
            try:
                response=client.post('http://127.0.0.1:8008/api/search/detect',files={'file':(Path(image_path).name,content,'image/png')},timeout=180)
                response.raise_for_status(); body=response.json()
                if body.get('fallback') or body.get('warnings'):raise RuntimeError('Detector fallback')
                detections=body['regions']; assessment=assess(detections,row['categoryID'],roi)
                correct=[dict(d,index=i+1) for i,d in enumerate(detections) if d['categoryID']==row['categoryID'] and plausible_product_box(d,roi)]
                result.update(rawResponse=body,assessment=assessment,bestCorrect=max(correct,key=lambda d:d['score'],default=None),
                              correctBoxCount=len(correct),correctLabelAnywhere=any(d['categoryID']==row['categoryID'] for d in detections),
                              boxCount=len(detections),overlay=f'boxes/{row["articleID"]}_{variant}.png')
                overlay(query,detections,roi).save(out/result['overlay'])
            except Exception as exc:
                result.update(status='error',error=type(exc).__name__)
                report['errors'].append({'articleID':row['articleID'],'variant':variant,'error':type(exc).__name__})
            result['seconds']=time.perf_counter()-start; row['variants'][variant]=result
            save_json(out/'partial_results.json',{**report,'currentProduct':row})
            a=result.get('assessment',{})
            print(f'#{row["articleID"]} {variant}: anyCorrect={a.get("anyCorrectProductBox")}, top={NAMES.get(a.get("predictedCategoryID"))}, boxes={result.get("boxCount")}',flush=True)
        report['cases'].append(row); save_json(out/'partial_results.json',report)
    success=lambda result:result.get('assessment',{}).get('anyCorrectProductBox',False)
    report['summary']={variant:{'tested':len(failed),'successful':sum(success(r['variants'][variant]) for r in report['cases']),
                               'successfulIDs':[r['articleID'] for r in report['cases'] if success(r['variants'][variant])],
                               'topCorrect':sum(r['variants'][variant].get('assessment',{}).get('isCorrect',False) for r in report['cases'])} for variant in VARIANTS}
    report['recoveredIDs']=[r['articleID'] for r in report['cases'] if any(success(r['variants'][v]) for v in VARIANTS[1:])]
    report['stillFailedIDs']=[r['articleID'] for r in report['cases'] if not any(success(r['variants'][v]) for v in VARIANTS)]
    report['status']='completed' if not report['errors'] else 'completed_with_errors'
    save_json(out/'report.json',report)
    lines=['# Khảo sát xoay/lật: 7 ảnh không có box đúng nhãn','',
           'Mỗi ô: Có/Không có box đúng nhãn; nếu có, kèm điểm cao nhất của box đúng.','',
           '| ID | Sản phẩm | '+' | '.join(LABELS[v] for v in VARIANTS)+' |',
           '|---:|---|'+'---|'*len(VARIANTS)]
    cards=[]
    with (out/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f); writer.writerow(['ID','Product','Variant','Status','AnyCorrectROI','BestCorrectScore','TopLabel','TopCorrect','BoxCount'])
        for row in report['cases']:
            cells=[]; panels=[]
            for v in VARIANTS:
                r=row['variants'][v]; a=r.get('assessment',{}); correct=r.get('bestCorrect')
                cells.append('Lỗi' if r['status']=='error' else f'Có ({correct["score"]:.4f})' if correct else 'Không')
                writer.writerow([row['articleID'],row['productName'],v,r['status'],success(r),correct['score'] if correct else '',NAMES.get(a.get('predictedCategoryID')),a.get('isCorrect'),r.get('boxCount')])
                panels.append(f'<section><h3>{LABELS[v]}: {cells[-1]}</h3><p>Top: {NAMES.get(a.get("predictedCategoryID"))}; top correct: {a.get("isCorrect")}</p><img src="{r.get("overlay",r["image"])}"></section>')
            lines.append(f'| {row["articleID"]} | {row["productName"].replace("|","/")} | '+' | '.join(cells)+' |')
            cards.append(f'<article><h2>#{row["articleID"]} {html.escape(row["productName"])}</h2><div>'+''.join(panels)+'</div></article>')
    lines+=['','## Tổng hợp','',f'Có ít nhất một biến đổi thành công: {report["recoveredIDs"]}',f'Vẫn không có box đúng ở mọi phiên bản: {report["stillFailedIDs"]}',f'Lỗi thực thi: {len(report["errors"])}','']
    for v,s in report['summary'].items():lines.append(f'- {LABELS[v]}: có box đúng {s["successful"]}/7; box cao điểm nhất đúng {s["topCorrect"]}/7.')
    lines+=['','## Giới hạn','']+['- '+s for s in report['limits']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    (out/'index.html').write_text('<meta charset="utf-8"><title>OWLv2 rotations and flips</title><style>body{font:15px system-ui;margin:25px}pre{white-space:pre-wrap}article{border:1px solid #ccc;padding:15px;margin:20px 0}article div{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}img{width:100%}</style><pre>'+html.escape('\n'.join(lines))+'</pre>'+''.join(cards),encoding='utf-8')
    print(json.dumps({'output':str(out),'summary':report['summary'],'recoveredIDs':report['recoveredIDs'],'stillFailedIDs':report['stillFailedIDs'],'errors':report['errors']},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()

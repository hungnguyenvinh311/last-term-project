"""Read-only live OWLv2 audit of every catalogue tablet/watch source photograph."""
import sys,json,hashlib,time,html
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from scripts.screen_shape_confusion import assess,overlay,summarize
from PIL import Image
import requests

NAMES={1:'Phone',2:'Laptop',3:'Tablet',4:'Headphones',5:'Watch',None:'MISSED'}


def main():
    previous=json.loads((ROOT/'data/screen_confusion_tests/report.json').read_text(encoding='utf-8'))
    catalog=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    selected=[p for p in catalog if p['categoryID'] in (3,5) and p.get('isActive')]
    assert {p['articleID'] for p in selected}=={r['articleID'] for r in previous['cases']},'Catalogue coverage changed'
    by_id={p['articleID']:p for p in selected}
    out=ROOT/'data/detector_single_box_audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False); (out/'boxes').mkdir()
    client=requests.Session(); response=client.get('http://127.0.0.1:8008/api/health',timeout=20)
    response.raise_for_status(); health=response.json()
    assert health['detectorProvider']=='owlv2' and health['detectorPadding'] is True,'Unexpected active detector'
    report={'provider':'owlv2','padding':True,'device':health['detectorDevice'],'threshold':.15,'maxReturnedBoxes':12,
            'labelPolicy':health.get('detectorLabelPolicy','raw'),
            'source':'Live POST /api/search/detect','cases':[],
            'limits':['All 20 tablet records and 20 watch records; 37 unique source photographs because three tablet pairs duplicate photos.',
                      'Original full source photos, not composed or manually cropped. Existing frozen coarse product ROIs used only for evaluation.',
                      'Reports both any phone-labelled box anywhere and phone-labelled boxes in the product ROI; promotional decorations may lie outside it.',
                      'Top1 means highest-confidence plausible box in the product ROI, not exact object-box IoU/mAP.',
                      'Active API keeps boxes above .15, top 12, without NMS; no model, threshold, prompt or ranking modifications.',
                      'Inference errors/fallbacks are not counted as successful no-phone detections.',
                      'If labelPolicy=provided_catalogue, these are label-guided retained boxes with transform recovery, not raw zero-shot predictions.']}
    for i,old in enumerate(previous['cases'],1):
        path=ROOT/by_id[old['articleID']]['imagePath']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==old['sourceSHA256'],'Source image changed'
        start=time.perf_counter()
        with path.open('rb') as f:
            response=client.post('http://127.0.0.1:8008/api/search/detect',files={'file':(path.name,f,'image/jpeg')},timeout=180)
        response.raise_for_status(); body=response.json()
        if body.get('fallback') or body.get('warnings'):raise RuntimeError('Detector unavailable: '+str(body.get('message','fallback')))
        detections=body['regions']; assessment=assess(detections,old['categoryID'],old['traits']['coarseProductROI'])
        row={k:old[k] for k in ('articleID','categoryID','productName','imagePath','sourceSHA256','traits')}
        row.update(original={'detections':detections,'assessment':assessment},seconds=time.perf_counter()-start,
                   rawResponse=body,overlay=f'boxes/{old["articleID"]}.png')
        with Image.open(path) as photo:overlay(photo.convert('RGB'),detections,old['traits']['coarseProductROI']).save(out/row['overlay'])
        report['cases'].append(row); save_json(out/'partial_results.json',report)
        print(f'{i}/40 #{row["articleID"]}: top={NAMES[assessment["predictedCategoryID"]]}, anyPhone={assessment["anyPhoneProductBox"]}, boxes={len(detections)}',flush=True)
    report['summary']={}
    for cid,name in [(3,'tablets'),(5,'watches')]:
        rows=[r for r in report['cases'] if r['categoryID']==cid]
        summary=summarize(rows,'original'); summary['uniqueSourceImages']=summarize(rows,'original',True)
        for key,field in [('topPhoneIDs','isPhone'),('anyPhoneProductIDs','anyPhoneProductBox')]:
            summary[key]=[r['articleID'] for r in rows if r['original']['assessment'][field]]
        summary['anyPhoneAnywhereIDs']=[r['articleID'] for r in rows if any(d['categoryID']==1 for d in r['original']['detections'])]
        summary['otherIncorrectTopIDs']=[r['articleID'] for r in rows if not r['original']['assessment']['isCorrect'] and not r['original']['assessment']['isPhone']]
        report['summary'][name]=summary
    save_json(out/'report.json',report)
    lines=['# Ảnh riêng lẻ: tablet/watch với OWLv2 + padding','',
           '| Nhóm | Số ảnh | Top1 đúng | Top1 thành Phone | Có box Phone trong vùng sản phẩm | Có box Phone ở bất kỳ đâu |',
           '|---|---:|---:|---:|---:|---:|']
    for name,s in report['summary'].items():
        lines.append(f'| {name} | {s["images"]} | {s["correctTop1"]} | {s["phoneTop1"]} | {s["phoneAnyBox"]} | {s["rawPhoneAnyBox"]} |')
        lines.extend(['',f'{name} — top Phone IDs: {s["topPhoneIDs"]}',f'{name} — any product Phone IDs: {s["anyPhoneProductIDs"]}',f'{name} — other wrong top IDs: {s["otherIncorrectTopIDs"]}',''])
    lines+=['## Tất cả sản phẩm','', '| ID | Nhóm đúng | Tổng box | Nhãn top trong vùng | Điểm top | Có box Phone trong vùng | Có box đúng nhãn trong vùng |','|---:|---|---:|---|---:|---|---|']
    cards=[]
    for r in report['cases']:
        a=r['original']['assessment']; top=a['strongestProductDetection']; ds=r['original']['detections']
        score=f'{top["score"]:.4f}' if top else '-'
        lines.append(f'| {r["articleID"]} | {NAMES[r["categoryID"]]} | {len(ds)} | {NAMES[a["predictedCategoryID"]]} | {score} | {a["anyPhoneProductBox"]} | {a["anyCorrectProductBox"]} |')
        details=''.join(f'<tr><td>{i}</td><td>{NAMES[d["categoryID"]]}</td><td>{d["score"]:.6f}</td></tr>' for i,d in enumerate(ds,1))
        cards.append(f'<article><h2>#{r["articleID"]} {html.escape(r["productName"])}</h2><p>Expected: {NAMES[r["categoryID"]]}; top: {NAMES[a["predictedCategoryID"]]} {score}; phone in ROI: {a["anyPhoneProductBox"]}</p><img src="{r["overlay"]}"><table><tr><th>Box</th><th>Label</th><th>Score</th></tr>{details}</table></article>')
    lines+=['','## Giới hạn','']+['- '+s for s in report['limits']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    (out/'index.html').write_text('<meta charset="utf-8"><style>body{font:16px system-ui;max-width:1100px;margin:30px auto}img{width:600px;max-width:100%}article{border:1px solid #ccc;padding:15px;margin:20px 0}td,th{border:1px solid #ccc;padding:5px}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><pre>'+html.escape('\n'.join(lines))+'</pre>'+''.join(cards),encoding='utf-8')
    print(json.dumps({'output':str(out),'summary':report['summary']},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()

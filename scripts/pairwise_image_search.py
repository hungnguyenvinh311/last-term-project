"""Real pairwise detection/retrieval experiment; records failures without altering labels."""
import sys,json,argparse,time,uuid,hashlib,html,math,os
from itertools import combinations
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageOps,ImageDraw,ImageFont
from fastapi.testclient import TestClient
from Model.application.config.settings import ROOT
from Model.application.config.ranking import load_search_weights
from DAO.application.dao.connection import Database
from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
from crawler.database.importer import initialize,import_products
from crawler.storage.files import save_json
from scripts.migrate import migrate
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.retrieval.representations import metadata,valid
from Model.application.ai.MultimodalEmbedderService import MultimodalEmbedderService
from bootstrap import create_app

NAMES={1:'phone',2:'laptop',3:'tablet',4:'headphones',5:'watch'}

def representatives(products):
    selected=[]
    for category in range(1,6):
        rows=[p for p in products if p['categoryID']==category and p.get('isActive') and p.get('imagePath')]
        if not rows:raise ValueError('Missing category '+str(category))
        selected.append(min(rows,key=lambda p:p['articleID']))
    return selected

def pair_specs(selected):
    if len(selected)!=5 or {p['categoryID'] for p in selected}!={1,2,3,4,5}:raise ValueError('Exactly five distinct categories required')
    return list(combinations(sorted(selected,key=lambda p:p['categoryID']),2))

def compose_pair(left,right,root=ROOT,panel=600):
    # The query contains only unmodified source photographs on a neutral canvas.
    # No class text, ID or expected-answer annotation is drawn onto the query.
    canvas=Image.new('RGB',(2*panel,panel),'white');targets=[]
    for index,p in enumerate((left,right)):
        with Image.open(root/p['imagePath']) as source:
            photo=ImageOps.contain(source.convert('RGB'),(panel-48,panel-48))
        x=index*panel+(panel-photo.width)//2;y=(panel-photo.height)//2
        canvas.paste(photo,(x,y))
        targets.append({'articleID':p['articleID'],'categoryID':p['categoryID'],'productName':p['productName'],
                        'sourceImage':p['imagePath'],'panelRegion':[index/2,0,(index+1)/2,1],
                        'sourceImageRegion':[x/(2*panel),y/panel,(x+photo.width)/(2*panel),(y+photo.height)/panel]})
    return canvas,targets

def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))

def located_in_panel(detection,panel):
    r=detection.get('region')
    if not isinstance(r,list) or len(r)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in r):return False
    area=(r[2]-r[0])*(r[3]-r[1])
    if r[2]<=r[0] or r[3]<=r[1]:return False
    cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
    return panel[0]<cx<panel[2] and panel[1]<=cy<=panel[3] and overlap(r,panel)/area>=.8

def detection_for_target(detections,target):
    local=[dict(d,detectorIndex=i+1) for i,d in enumerate(detections) if located_in_panel(d,target['panelRegion'])]
    strongest=max(local,key=lambda d:d['score'],default=None)
    matching=[d for d in local if d.get('categoryID')==target['categoryID']]
    return strongest,max(matching,key=lambda d:d['score'],default=None)

def search_summary(body,target):
    rows=body.get('products',[]);ids=[p['articleID'] for p in rows]
    return {'returnedIDs':ids,'returnedCategories':[p['categoryID'] for p in rows],
            'sourceRank':ids.index(target['articleID'])+1 if target['articleID'] in ids else None,
            'sourceInTop5':target['articleID'] in ids[:5],
            'expectedCategoryOnly':bool(rows) and all(p['categoryID']==target['categoryID'] for p in rows),
            'resolvedCategoryID':body.get('criteria',{}).get('categoryID'),
            'topResults':[{key:p.get(key) for key in ('articleID','categoryID','productName','score','matchDetails')} for p in rows[:5]]}

def search(client,content,region,category,target):
    try:
        r=client.post('/api/search/image',files={'file':('pair.png',content,'image/png')},data={'region':json.dumps(region),'imageCategoryID':str(category)})
        if r.status_code!=200:return {'status':'error','httpStatus':r.status_code,'error':r.json().get('detail','Search failed')}
        result=search_summary(r.json(),target)
        result['selectedCategoryBoundaryHeld']=all(c==category for c in result['returnedCategories'])
        result['status']='passed' if result['expectedCategoryOnly'] and result['sourceInTop5'] else 'failed'
        return result
    except Exception as exc:return {'status':'error','errorType':type(exc).__name__}

def draw_detections(photo,detections,targets):
    result=photo.copy();draw=ImageDraw.Draw(result)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for index,d in enumerate(detections):
        box=[d['region'][0]*photo.width,d['region'][1]*photo.height,d['region'][2]*photo.width,d['region'][3]*photo.height]
        if box[2]<box[0] or box[3]<box[1]:continue
        colour=['#d44b19','#007c68','#255bce','#9c329b','#9e7200'][index%5]
        draw.rectangle(box,outline=colour,width=3)
        text=f'{index+1}: {d["label"]} {d["score"]:.3f}'
        x=box[0];y=max(0,box[1]-24);bounds=draw.textbbox((x,y),text,font=font)
        draw.rectangle(bounds,fill='white');draw.text((x,y),text,fill=colour,font=font)
    draw.line([(photo.width/2,0),(photo.width/2,photo.height)],fill='#888888',width=2)
    return result

def render_report(output,report):
    summary=report['summary'];cards=[]
    for pair in report['pairs']:
        target_rows=[]
        for target in pair['targets']:
            top=target['strongestLocatedDetection'];observed=top['label'] if top else 'MISSED'
            end=target['detectedRegionSearch'];control=target['knownRegionControl']
            target_rows.append(f'<tr><td>#{target["articleID"]} {html.escape(target["productName"])}</td><td>{html.escape(observed)}</td><td>{end["status"]}</td><td>{control["status"]}</td></tr>')
        cards.append(f'<article><h2>{pair["pairID"]}</h2><p><a href="{pair["queryImage"]}">Ảnh ghép gốc</a> · <a href="{pair["detectionsImage"]}">Ảnh có bounding box</a></p><img src="{pair["detectionsImage"]}"><table><tr><th>Sản phẩm nguồn</th><th>Nhãn mạnh nhất trong vùng</th><th>Search từ nhận diện</th><th>Đối chiếu vùng đã biết</th></tr>'+''.join(target_rows)+'</table></article>')
    page='<!doctype html><meta charset="utf-8"><title>Pairwise image search experiment</title><style>body{font:15px system-ui;max-width:1200px;margin:30px auto}article{padding:20px;border:1px solid #ddd;margin:20px 0}img{width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px;text-align:left}</style>'
    page+=f'<h1>10 ảnh ghép, 20 sản phẩm cần kiểm tra</h1><p>Đúng nhãn mạnh nhất: {summary["strongestLabelCorrect"]}/20. Có ít nhất một nhãn đúng trong vùng: {summary["correctLabelAvailable"]}/20. Search từ vùng nhận diện đạt: {summary["endToEndPassed"]}/20. Đối chiếu vùng đã biết đạt: {summary["knownRegionPassed"]}/20.</p>'
    if report.get('byCategory'):
        page+='<table><tr><th>Nhóm</th><th>Đúng nhãn mạnh nhất</th><th>Search từ nhận diện đạt</th><th>Đối chiếu đạt</th></tr>'+''.join(f'<tr><td>{name}</td><td>{r["strongestLabelCorrect"]}/{r["targets"]}</td><td>{r["endToEndPassed"]}/{r["targets"]}</td><td>{r["knownRegionPassed"]}/{r["targets"]}</td></tr>' for name,r in report['byCategory'].items())+'</table>'
    page+='<p>Ảnh ghép lấy từ danh mục đã lập chỉ mục. Đây là kiểm tra tính nhất quán, không phải độ chính xác trên ảnh khách hàng độc lập. Vị trí được đối chiếu với ô chứa ảnh nguồn; chưa có bounding box gán nhãn thủ công cho từng vật thể. Vùng đối chiếu không thay thế kết quả nhận diện.</p>'
    (output/'index.html').write_text(page+''.join(cards),encoding='utf-8')
    lines=['# Pairwise image search experiment','',json.dumps(summary,ensure_ascii=False,indent=2),'',
           '| Pair | Source ID | Strongest label correct | Correct label available | Detected-region search | Known-region control |',
           '|---|---:|---|---|---|---|']
    for pair in report['pairs']:
        for t in pair['targets']:
            lines.append(f'| {pair["pairID"]} | {t["articleID"]} | {t["strongestLabelCorrect"]} | {t["bestCorrectDetection"] is not None} | {t["detectedRegionSearch"]["status"]} | {t["knownRegionControl"]["status"]} |')
    lines+=['','## Limits','']+['- '+v for v in report['limits']]
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def run(output):
    output=Path(output).resolve();output.relative_to((ROOT/'data').resolve())
    if output.exists():raise RuntimeError('Output exists; choose a new directory to retain prior images/results')
    products=ProductDAOImpl(Database()).findActive();manifest=metadata();identity=MultimodalEmbedderService().identity
    if not products or not all(valid(p,manifest,identity) for p in products):raise RuntimeError('Catalogue representations are not fully compatible')
    selected=representatives(products);specs=pair_specs(selected)
    output.mkdir(parents=True,exist_ok=False);(output/'images').mkdir();(output/'detections').mkdir()
    name='ecommerce_test_pair_'+uuid.uuid4().hex[:10]
    initialize(name)
    records=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    import_products(records,name);migrate(name)
    target_dao=ProductDAOImpl(Database(name))
    for p in products:target_dao.saveRepresentation(p['articleID'],p['imageEmbedding'],p['textEmbedding'])
    app=create_app(name,{'intent':IntentExtractorService()})
    report={'database':name,'encoder':identity,'detectorClass':app.state.services['search'].detector.__class__.__name__,
            'detectorModel':os.getenv('APP_DETECTOR_MODEL','google/owlvit-base-patch32'),'detectorThreshold':.15,
            'weights':load_search_weights(),'representatives':[{k:p.get(k) for k in ('articleID','categoryID','productName','imagePath')} for p in selected],
            'pairPolicy':'All 10 unordered category pairs; each category appears four times. One catalogue representative per category.',
            'localizationPolicy':'Detection centre inside expected panel and >=80% detection area inside panel. This is panel localization, not exact object-box IoU.',
            'selectionPolicy':'Highest-confidence localized detection, retaining its actual label even when wrong; no ground-truth label substitution.',
            'pairs':[],'limits':['One product per category, one left/right layout; no claim of exhaustive product/angle/background coverage.',
                                'Indexed catalogue images are reused; top-five source recovery is a consistency check, not independent retrieval accuracy.',
                                'Panels and pasted-image rectangles are known; exact physical-object boxes are not manually annotated.',
                                'Correct-label availability is separate from strongest-label correctness; duplicates/extra detections are retained.',
                                'Known-region controls use the expected category explicitly and are reported separately from end-to-end detection.',
                                'No Gemini API calls, live ranking changes, catalogue modifications or demo search-history writes. Test database is retained.']}
    save_json(output/'run.json',{k:v for k,v in report.items() if k!='pairs'})
    start=time.perf_counter()
    with TestClient(app) as client:
        for index,(left,right) in enumerate(specs,1):
            pairID=f'{NAMES[left["categoryID"]]}__{NAMES[right["categoryID"]]}'
            photo,targets=compose_pair(left,right);image_file=output/'images'/f'{pairID}.png';photo.save(image_file);content=image_file.read_bytes()
            response=client.post('/api/search/detect',files={'file':(image_file.name,content,'image/png')})
            body=response.json();detections=body.get('regions',[])
            pair={'pairID':pairID,'queryImage':f'images/{pairID}.png','querySHA256':hashlib.sha256(content).hexdigest(),
                  'detectionsImage':f'detections/{pairID}.png','detectionHTTPStatus':response.status_code,
                  'detectorFallback':body.get('fallback',True),'detectorMessage':body.get('message'),
                  'detections':detections,'targets':[]}
            draw_detections(photo,detections,targets).save(output/pair['detectionsImage'])
            for expected in targets:
                strongest,best_correct=detection_for_target(detections,expected)
                end=search(client,content,strongest['region'],strongest['categoryID'],expected) if strongest and strongest.get('categoryID') else {'status':'skipped_no_located_detection'}
                control=search(client,content,expected['sourceImageRegion'],expected['categoryID'],expected)
                pair['targets'].append({**expected,'strongestLocatedDetection':strongest,'bestCorrectDetection':best_correct,
                                        'strongestLabelCorrect':bool(strongest and strongest.get('categoryID')==expected['categoryID']),
                                        'detectedRegionSearch':end,'knownRegionControl':control})
            report['pairs'].append(pair);save_json(output/'partial_results.json',report)
            print(f'{index}/10 {pairID}: '+', '.join(f'{t["articleID"]} detect={t["strongestLabelCorrect"]} search={t["detectedRegionSearch"]["status"]} control={t["knownRegionControl"]["status"]}' for t in pair['targets']),flush=True)
    targets=[t for pair in report['pairs'] for t in pair['targets']]
    report['byCategory']={NAMES[cid]:{
        'targets':sum(t['categoryID']==cid for t in targets),
        'strongestLabelCorrect':sum(t['categoryID']==cid and t['strongestLabelCorrect'] for t in targets),
        'endToEndPassed':sum(t['categoryID']==cid and t['detectedRegionSearch']['status']=='passed' for t in targets),
        'knownRegionPassed':sum(t['categoryID']==cid and t['knownRegionControl']['status']=='passed' for t in targets)} for cid in range(1,6)}
    report['summary']={'pairs':len(report['pairs']),'targets':len(targets),
        'strongestLabelCorrect':sum(t['strongestLabelCorrect'] for t in targets),
        'correctLabelAvailable':sum(t['bestCorrectDetection'] is not None for t in targets),
        'endToEndPassed':sum(t['detectedRegionSearch']['status']=='passed' for t in targets),
        'knownRegionPassed':sum(t['knownRegionControl']['status']=='passed' for t in targets),
        'detectedSearchAttempts':sum(t['detectedRegionSearch']['status']!='skipped_no_located_detection' for t in targets),
        'selectedCategoryBoundaryFailures':sum(t['detectedRegionSearch'].get('selectedCategoryBoundaryHeld') is False for t in targets),
        'seconds':time.perf_counter()-start}
    report['status']='completed_observational_experiment'
    save_json(output/'report.json',report);render_report(output,report)
    print(json.dumps(report['summary'],ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'data/pairwise_search_tests'))
    run(parser.parse_args().output)

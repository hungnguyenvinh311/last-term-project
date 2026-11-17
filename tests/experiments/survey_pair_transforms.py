"""Six-view live API audit of tablet__watch; panels move with image geometry."""
import sys,json,hashlib,time,html
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from tests.experiments.survey_rotations_flips import transform,VARIANTS,LABELS,NAMES
from tests.experiments.survey_pair_boxes import analyze
from PIL import Image,ImageDraw,ImageFont
import requests


def main():
    source=ROOT/'data/pairwise_search_tests'
    pair=next(p for p in json.loads((source/'report.json').read_text(encoding='utf-8'))['pairs'] if p['pairID']=='tablet__watch')
    path=source/pair['queryImage']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==pair['querySHA256']
    with Image.open(path) as photo: original=photo.convert('RGB')
    out=ROOT/'data/detector_pair_transform_audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False); (out/'images').mkdir();(out/'boxes').mkdir()
    client=requests.Session(); response=client.get('http://127.0.0.1:8008/api/health',timeout=20)
    response.raise_for_status();health=response.json()
    assert health['detectorProvider']=='owlv2' and health['detectorPadding']
    report={'pairID':pair['pairID'],'inputSHA256':pair['querySHA256'],'provider':'owlv2','padding':True,
            'device':health['detectorDevice'],'threshold':.15,'maxReturnedBoxes':12,'variants':[],
            'limits':['Single previously observed synthetic pair, not an independent accuracy estimate.',
                      'Success is any correctly labelled box in the transformed target panel, not exact object IoU.',
                      'Target panels rotate/flip with the whole image; ground truth never enters model inference.',
                      'Clockwise rotations; same threshold, queries and top-12 policy. No production changes.']}
    save_json(out/'preregistered.json',{**report,'plannedVariants':VARIANTS})
    lines=['# Xoay/lật ảnh ghép tablet__watch','',
           '| Biến đổi | Tổng box | Box vùng tablet | Có box Tablet đúng | Top vùng tablet | Box vùng watch | Có box Watch đúng | Top vùng watch |',
           '|---|---:|---:|---|---|---:|---|---|']
    cards=[]
    for variant in VARIANTS:
        image,_=transform(original,[0,0,1,1],variant)
        targets=[{**t,'panelRegion':transform(original,t['panelRegion'],variant)[1]} for t in pair['targets']]
        imagefile=f'images/{variant}.png'; image.save(out/imagefile)
        start=time.perf_counter()
        response=client.post('http://127.0.0.1:8008/api/search/detect',files={'file':(variant+'.png',(out/imagefile).read_bytes(),'image/png')},timeout=180)
        response.raise_for_status();body=response.json()
        if body.get('fallback') or body.get('warnings'):raise RuntimeError('Detector fallback')
        row={'variant':variant,'image':imagefile,'transformedTargets':targets,'rawResponse':body,
             'seconds':time.perf_counter()-start,**analyze(body['regions'],targets),'overlay':f'boxes/{variant}.png'}
        marked=image.copy();draw=ImageDraw.Draw(marked);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
        for t in targets:
            r=t['panelRegion'];draw.rectangle([r[0]*image.width,r[1]*image.height,r[2]*image.width-1,r[3]*image.height-1],outline='#888888',width=2)
        for i,d in enumerate(body['regions'],1):
            r=d['region'];box=[r[0]*image.width,r[1]*image.height,r[2]*image.width,r[3]*image.height]
            color={1:'#cc3300',2:'#886600',3:'#0033cc',4:'#880088',5:'#007755'}[d['categoryID']]
            draw.rectangle(box,outline=color,width=3);x,y=box[0],max(0,box[1]-22)
            text=f'#{i} {NAMES[d["categoryID"]]} {d["score"]:.4f}'; bounds=draw.textbbox((x,y),text,font=font)
            draw.rectangle(bounds,fill='white');draw.text((x,y),text,font=font,fill=color)
        marked.save(out/row['overlay']);report['variants'].append(row);save_json(out/'partial_results.json',report)
        tablet,watch=row['targets']
        def top(t):return f'{NAMES[t["top"]["categoryID"]]} {t["top"]["score"]:.4f}' if t['top'] else 'MISSED'
        cells=[LABELS[variant],str(row['totalBoxes']),str(tablet['boxCount']),'Có' if tablet['bestCorrect'] else 'Không',top(tablet),str(watch['boxCount']),'Có' if watch['bestCorrect'] else 'Không',top(watch)]
        lines.append('| '+' | '.join(cells)+' |')
        cards.append(f'<article><h2>{LABELS[variant]}</h2><p>{html.escape(" | ".join(cells))}</p><img src="{row["overlay"]}"></article>')
        print(' | '.join(cells),flush=True)
    report['status']='completed';save_json(out/'report.json',report)
    lines+=['','## Giới hạn','']+['- '+s for s in report['limits']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    (out/'index.html').write_text('<meta charset="utf-8"><style>body{font:16px system-ui;max-width:1200px;margin:30px auto}img{max-width:100%;max-height:950px}pre{white-space:pre-wrap}article{padding:15px;border:1px solid #ccc;margin:20px 0}</style><pre>'+html.escape('\n'.join(lines))+'</pre>'+''.join(cards),encoding='utf-8')
    print(str(out),flush=True)


if __name__=='__main__':main()

"""Verify the provided-label policy across every active catalogue photo."""
import sys,json,time,html
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
import requests


def main():
    products=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    products=[p for p in products if p.get('isActive')]
    out=ROOT/'data/provided_catalogue_verification'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    client=requests.Session(); response=client.get('http://127.0.0.1:8008/api/health',timeout=20)
    response.raise_for_status();assert response.json()['detectorLabelPolicy']=='provided_catalogue'
    report={'policy':'provided_catalogue','cases':[],'errors':[],'limits':'Assisted label selection on supplied photos, not raw detector accuracy.'}
    for i,p in enumerate(products,1):
        start=time.perf_counter()
        with (ROOT/p['imagePath']).open('rb') as f:
            response=client.post('http://127.0.0.1:8008/api/search/detect',files={'file':('catalogue.jpg',f,'image/jpeg')},timeout=180)
        response.raise_for_status();body=response.json()
        if body.get('fallback'):raise RuntimeError(body.get('message','Detector fallback'))
        regions=body['regions']
        assert len(regions)<=1 and all(r['categoryID']==p['categoryID'] for r in regions)
        row={'articleID':p['articleID'],'productName':p['productName'],'categoryID':p['categoryID'],
             'resolved':len(regions)==1,'response':body,'seconds':time.perf_counter()-start}
        report['cases'].append(row);save_json(out/'partial_results.json',report)
        print(f'{i}/{len(products)} #{p["articleID"]}: resolved={row["resolved"]}',flush=True)
    report['summary']={str(cid):{'total':sum(p['categoryID']==cid for p in report['cases']),
        'resolved':sum(p['categoryID']==cid and p['resolved'] for p in report['cases']),
        'missingIDs':[p['articleID'] for p in report['cases'] if p['categoryID']==cid and not p['resolved']]} for cid in range(1,6)}
    save_json(out/'report.json',report)
    lines=['# Supplied catalogue verification','',report['limits'],'','| Category | Resolved | Total | Missing IDs |','|---|---:|---:|---|']
    for cid,s in report['summary'].items():lines.append(f'| {cid} | {s["resolved"]} | {s["total"]} | {s["missingIDs"]} |')
    lines+=['','## Missing products','']+[f'- #{r["articleID"]}: {r["productName"]}' for r in report['cases'] if not r['resolved']]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'output':str(out),'summary':report['summary']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()

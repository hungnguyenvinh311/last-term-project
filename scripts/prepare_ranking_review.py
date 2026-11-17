"""Create reviewable suggestions, never automatically approved ground truth."""
import sys,json,random,hashlib,html,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from Model.application.normalization import model_key,fold
from crawler.storage.files import save_json

CATEGORY={1:'điện thoại',2:'laptop',3:'máy tính bảng',4:'tai nghe',5:'đồng hồ'}

def build(records):
    # Connected groups keep identical images and model variants in one split.
    groups=[]
    for p in records:
        keys={'model:'+model_key(p),'image:'+hashlib.sha256((ROOT/p['imagePath']).read_bytes()).hexdigest()}
        touching=[g for g in groups if g['keys']&keys]
        merged={'keys':set(keys),'products':[p]}
        for g in touching:
            merged['keys']|=g['keys'];merged['products']+=g['products'];groups.remove(g)
        groups.append(merged)
    rng=random.Random(20261104);cases=[]
    for cid in range(1,6):
        available=sorted([g for g in groups if all(p['categoryID']==cid for p in g['products'])],key=lambda g:min(p['articleID'] for p in g['products']))
        rng.shuffle(available)
        if len(available)<4:raise ValueError('Need four distinct model/image groups per category')
        for index,g in enumerate(available[:4]):
            p=min(g['products'],key=lambda p:p['articleID'])
            group='product-group-'+hashlib.sha256('|'.join(sorted(g['keys'])).encode()).hexdigest()[:12]
            truth=sorted(x['articleID'] for x in g['products'])
            split='validation' if index<2 else 'test'
            for kind in ('text','image','image_text'):
                text=(CATEGORY[cid]+' '+p['productName']) if kind=='text' else ('' if kind=='image' else CATEGORY[cid]+(' '+p['brand'] if p.get('brand') else ''))
                cases.append({'caseID':f'{kind}-{p["articleID"]}','kind':kind,'split':split,'groupID':group,
                              'text':text,'image':p['imagePath'] if kind!='text' else None,
                              'sourceArticleID':p['articleID'],'relevantArticleIDs':truth,'reviewed':False,
                              'labelOrigin':'automatic catalogue/model/image-identity suggestion; needs human review',
                              'queryOrigin':'catalogue title' if kind=='text' else 'catalogue image already indexed; optimistic self-retrieval diagnostic',
                              'reviewNotes':''})
    return cases

def main():
    records=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    out=ROOT/'data/evaluation/ranking_review';out.mkdir(parents=True,exist_ok=True)
    target=out/'cases.json'
    if target.exists():raise RuntimeError('Review already exists: refusing to overwrite human edits')
    cases=build(records);save_json(target,cases)
    render_review(records,cases,out)
    print('Created 60 unreviewed cases and HTML/Markdown review sheets; no database writes.')

def render_review(records,cases,out):
    reviewed=sum(c.get('reviewed') is True for c in cases)
    status=f'{reviewed}/{len(cases)} labels reviewed'
    by_id={p['articleID']:p for p in records}
    cards=[];lines=['# Ranking query review','',
        '60 catalogue queries: 20 text, 20 image, 20 image + text. '+status+'.',
        '30 validation and 30 held-out test queries, separated by connected model/image groups.',
        'These catalogue-derived queries are optimistic diagnostics, not external customer-query accuracy.',
        'Review every relevantArticleIDs list against the full catalogue, not just the suggested source. Add every genuinely relevant ID; use [] for no-answer queries.',
        'Edit cases.json: correct text/labels, add reviewNotes and set reviewed=true only after review. Keep groupID and split consistent. Do not inspect test rankings to adjust validation weights.',
        'Colour-critical queries and new external photos must be added before production tuning. A model-level record may not identify the exact colour pictured.',
        '', '| Case | Split | Query | Proposed relevant products |','|---|---|---|---|']
    for c in cases:
        p=by_id[c['sourceArticleID']];label='; '.join(f'{i}: {by_id[i]["productName"]}' for i in c['relevantArticleIDs'])
        image=os.path.relpath(ROOT/p['imagePath'],out).replace('\\','/')
        text=c['text'] or '(Image only)'
        lines.append(f'| {c["caseID"]} | {c["split"]} | {text.replace("|","/")} | {label.replace("|","/")} |')
        label_status='REVIEWED' if c.get('reviewed') else 'UNREVIEWED'
        cards.append(f'<article><img src="{html.escape(image)}"><div><h3>{html.escape(c["caseID"])}</h3><b>{c["split"]} · {label_status}</b><p>{html.escape(text)}</p><p>Relevant: {html.escape(label)}</p><small>{html.escape(c["queryOrigin"])}</small></div></article>')
    (out/'review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Ranking query review</title><style>body{font:15px system-ui;max-width:1100px;margin:30px auto}article{display:flex;gap:24px;border:1px solid #ddd;padding:18px;margin:12px 0}img{width:160px;height:150px;object-fit:contain}small{color:#666}</style><h1>Ranking query review — '+status+'</h1><p>Catalogue-derived diagnostics. Product colours and external customer queries need separate review.</p>'+''.join(cards),encoding='utf-8')
    colour_rows=[p for p in records if any('mau' in fold(k) or 'color' in fold(k) or 'colour' in fold(k) for k in (p.get('technicalSpecs') or {}))]
    save_json(out/'catalogue_audit.json',{'products':len(records),'withColourSpecification':len(colour_rows),'colourSpecificationIDs':[p['articleID'] for p in colour_rows],
        'caseCount':len(cases),'splitSeed':20261104,'reviewedCases':reviewed,
        'warning':'Image appearance is not a verified colour attribute. Missing metadata cannot be fixed by ranking weights.'})

if __name__=='__main__':main()

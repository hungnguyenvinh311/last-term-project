"""Record the user's explicit label confirmation, preserving unapproved stress cases."""
import sys,json,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from scripts.prepare_ranking_review import CATEGORY,render_review

def main():
    out=ROOT/'data/evaluation/ranking_review';file=out/'cases.json'
    cases=json.loads(file.read_text(encoding='utf-8'))
    records=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    by_id={p['articleID']:p for p in records}
    if len(cases)!=60 or any(c.get('reviewed') for c in cases):raise RuntimeError('Only the original 60 unreviewed cases are covered by this confirmation')
    backup=out/'cases_before_user_confirmation.json'
    if backup.exists():raise RuntimeError('Confirmation snapshot already exists; refusing to overwrite')
    shutil.copy2(file,backup)
    for c in cases:
        p=by_id[c['sourceArticleID']]
        if c['kind']=='image_text':c['text']=CATEGORY[p['categoryID']]+(' '+p['brand'] if p.get('brand') else '')
        c['reviewed']=True
        c['reviewNotes']='User confirmed remaining labels on 2026-11-04; product 79 corrected to Beats; promotional brand suffixes canonicalized. Catalogue-derived query limits remain.'
        c['labelOrigin']='user-confirmed catalogue query relevance, 2026-11-04'
    save_json(file,cases);render_review(records,cases,out)
    print('Confirmed 60 existing labels. The 12 incomplete customer stress queries remain unreviewed.')

if __name__=='__main__':main()

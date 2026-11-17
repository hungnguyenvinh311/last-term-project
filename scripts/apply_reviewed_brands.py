"""Apply user-confirmed retailer brand edits with snapshots; original provenance stays raw."""
import sys,json,shutil
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from Model.application.config.brands import canonical_brand
from DAO.application.dao.connection import Database
from crawler.storage.files import save_json

def corrected_products(records):
    products=json.loads(json.dumps(records));changes=[]
    if len({p['articleID'] for p in products})!=len(products):raise ValueError('Duplicate product IDs')
    target=next((p for p in products if p['articleID']==79),None)
    if not target or 'beats' not in target['productName'].casefold():raise ValueError('Product 79 is not the approved Beats record')
    for p in products:
        before=p.get('brand');after='Beats' if p['articleID']==79 else canonical_brand(before)
        if before!=after:
            changes.append({'articleID':p['articleID'],'before':before,'after':after})
            p['brand']=after
    return products,changes

def main():
    folder=ROOT/'data/retailer_catalog';file=folder/'products.json'
    raw=file.read_bytes();records=json.loads(raw);products,changes=corrected_products(records)
    db=Database()
    if db.options['database']!='ecommerce_vn_retailer_demo':raise RuntimeError('This correction only targets the approved retailer database')
    snapshot=folder/('brand_review_backup_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    snapshot.mkdir(exist_ok=False)
    (snapshot/'products.json').write_bytes(raw)
    if (folder/'embedding_manifest.json').exists():shutil.copy2(folder/'embedding_manifest.json',snapshot/'embedding_manifest.json')
    with db.transaction() as connection:
        rows=db.query('SELECT * FROM Products ORDER BY articleID FOR UPDATE',connection=connection)
        by_id={p['articleID']:p for p in rows}
        if set(by_id)!={p['articleID'] for p in records}:raise RuntimeError('Database/catalogue IDs differ')
        save_json(snapshot/'database_products_before.json',json.loads(json.dumps(rows,default=str)))
        for p in records:
            row=by_id[p['articleID']]
            if row['productName']!=p['productName'] or row.get('brand')!=p.get('brand'):
                raise RuntimeError('Database/catalogue differ; no automatic overwrite')
        for change in changes:
            db.query('UPDATE Products SET brand=%s WHERE articleID=%s',(change['after'],change['articleID']),connection)
        try:
            save_json(file,products)
        except BaseException:
            file.write_bytes(raw)
            raise
    save_json(snapshot/'changes.json',{'reviewedBy':'user confirmation 2026-11-04','changes':changes,
        'originalProvenanceUnchanged':True,'embeddingRegenerationRequired':bool(changes)})
    print(json.dumps({'changed':len(changes),'changes':changes,'backup':str(snapshot.relative_to(ROOT))},ensure_ascii=False))

if __name__=='__main__':main()

"""Persist observed colours of indexed photos; leave ambiguous photos unresolved."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from DAO.application.dao.connection import Database
from crawler.storage.files import save_json
from Model.application.ai.product_caption import PHOTO_COLOR_KEY

# Manually inspected contact sheets and product photos, not inferred by a model.
# Primary physical finish; for watches the visible strap is the primary colour.
# Screen wallpapers, packaging, text and variant-colour swatches are ignored.
OBSERVED={
 1:'purple',2:'orange',3:'gray',5:'black',7:'blue',8:'black',9:'gray',10:'purple',
 11:'black',12:'gray',13:'red',14:'orange',15:'red',16:'orange',17:'pink',18:'red',20:'purple',
 21:'gray',22:'gray',24:'gray',25:'gray',26:'gray',27:'silver',28:'gray',29:'black',30:'gray',
 31:'blue',32:'black',33:'gray',34:'black',35:'gray',36:'black',38:'gray',39:'black',40:'black',
 41:'silver',42:'gray',43:'gray',44:'blue',45:'blue',46:'silver',47:'gray',50:'black',51:'red',
 54:'blue',55:'silver',56:'blue',57:'black',58:'gray',60:'blue',
 61:'white',62:'silver',63:'white',64:'white',65:'black',66:'purple',67:'brown',68:'black',
 69:'gray',70:'gray',71:'white',72:'white',73:'white',74:'white',75:'white',76:'white',
 77:'white',78:'white',79:'red',80:'purple',
 81:'black',82:'black',83:'white',86:'black',88:'green',89:'black',91:'black',92:'black',93:'black',
 94:'black',97:'pink',99:'black',101:'blue',102:'pink',106:'black',107:'white',108:'white',
}

def annotations(records,root=ROOT):
    if set(OBSERVED)-{p['articleID'] for p in records}:raise ValueError('Annotation IDs do not match this catalogue')
    result=[]
    for p in records:
        colour=OBSERVED.get(p['articleID'])
        result.append({'articleID':p['articleID'],'productName':p['productName'],'imagePath':p['imagePath'],
                       'imageSHA256':hashlib.sha256((root/p['imagePath']).read_bytes()).hexdigest(),
                       'colour':colour,'status':'assistant_visual_review' if colour else 'needs_user_review',
                       'scope':'visible watch strap' if p['categoryID']==5 else 'visible physical body/earpieces',
                       'basis':'Manual visual inspection by assistant, not user-confirmed ground truth. Ignore screens and colour-option swatches.',
                       'notes':'' if colour else 'Uncertain finish, partial body visibility or ambiguous mixed colours; no hard colour label applied.'})
    return result

def apply_specs(records,entries):
    out=deepcopy(records);by_id={e['articleID']:e for e in entries}
    for p in out:
        entry=by_id[p['articleID']]
        if entry['status']=='assistant_visual_review' and entry['colour']:
            specs=dict(p.get('technicalSpecs') or {})
            if PHOTO_COLOR_KEY in specs and specs[PHOTO_COLOR_KEY]!=entry['colour']:
                raise ValueError('Do not overwrite an existing conflicting colour annotation')
            specs[PHOTO_COLOR_KEY]=entry['colour'];p['technicalSpecs']=specs
    return out

def main():
    folder=ROOT/'data/retailer_catalog';file=folder/'products.json';raw=file.read_bytes();records=json.loads(raw)
    target=folder/'color_annotations.json'
    if target.exists():raise RuntimeError('Colour annotations already exist; preserve review edits')
    entries=annotations(records);updated=apply_specs(records,entries)
    db=Database()
    if db.options['database']!='ecommerce_vn_retailer_demo':raise RuntimeError('Refuse updates outside the approved retailer database')
    backup=folder/('color_backup_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));backup.mkdir(exist_ok=False)
    (backup/'products.json').write_bytes(raw)
    (backup/'embedding_manifest.json').write_bytes((folder/'embedding_manifest.json').read_bytes())
    try:
        with db.transaction() as connection:
            rows=db.query('SELECT * FROM Products ORDER BY articleID FOR UPDATE',connection=connection)
            current={p['articleID']:p for p in rows}
            if set(current)!={p['articleID'] for p in records}:raise ValueError('Database IDs differ from catalogue')
            save_json(backup/'database_products_before.json',json.loads(json.dumps(rows,default=str)))
            for before,after in zip(records,updated):
                row=current[before['articleID']]
                if row['technicalSpecs']!=before['technicalSpecs']:raise ValueError('Database/catalogue specifications differ')
                if before['technicalSpecs']!=after['technicalSpecs']:
                    db.query('UPDATE Products SET technicalSpecs=%s WHERE articleID=%s',
                             (json.dumps(after['technicalSpecs'],ensure_ascii=False),after['articleID']),connection)
            save_json(file,updated)
    except BaseException:
        file.write_bytes(raw)
        raise
    save_json(target,entries)
    observed=sum(e['colour'] is not None for e in entries)
    print(json.dumps({'annotated':observed,'needsReview':len(entries)-observed,'backup':str(backup.relative_to(ROOT))}))

if __name__=='__main__':main()

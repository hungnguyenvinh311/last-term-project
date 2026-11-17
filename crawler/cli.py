import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import sys
from crawler.config.settings import ROOT,CATEGORIES
from crawler.storage.files import load_json,save_json
from crawler.normalization.products import category_of,normalize,identity,model_identity
from crawler.validation.catalog import validate

def prepare(limit,sample=False):
    from crawler.sources.bestbuy import fetch_snapshot,PROVIDER
    items=fetch_snapshot()
    normalized=ROOT/'data/normalized'
    keymap_path=normalized/'product_key_map.json'
    keys=load_json(keymap_path,{})
    if len(set(keys.values()))!=len(keys):raise ValueError('Duplicate IDs in key manifest')
    next_id=max(keys.values(),default=0)+1
    products=[];provenance=[];counts=Counter();seen=set();rejected=Counter()
    for item in sorted(items,key=lambda x:str(x.get('sku',''))):
        category=category_of(item)
        if not category or counts[category]>=limit:continue
        model=model_identity(item)
        if model in seen:rejected['duplicate_model']+=1;continue
        key=identity(item);article_id=keys.get(key,next_id)
        try:product=normalize(item,article_id,category)
        except ValueError:rejected['invalid_product']+=1;continue
        if key not in keys:keys[key]=article_id;next_id+=1
        seen.add(model);counts[category]+=1;products.append(product)
        provenance.append(dict(articleID=article_id,provider=PROVIDER,source_id=str(item['sku']),source_url=item.get('url'),
            source_dataset_url='https://github.com/BestBuyAPIs/open-data-set',license='CC0-1.0',source_category=item.get('category'),
            source_image_url=item.get('image'),image_status='not_downloaded_rights_unconfirmed',
            collected_at=datetime.now(timezone.utc).isoformat(),price_observation_date=None,
            price_basis='Historical source snapshot, not current live price',currency='USD'))
        if sample and len(products)>=5:break
    # Write key registry first so interrupted output writes cannot recycle an allocated ID.
    save_json(keymap_path,keys)
    out=ROOT/'data/sample' if sample else normalized
    save_json(out/'products.json',products);save_json(out/'provenance.json',provenance)
    save_json(out/'images_manifest.json',[])
    report=validate(products,provenance,target=limit);report['rejections']=dict(rejected)
    save_json(out/'validation_report.json',report)
    return report

def main():
    parser=argparse.ArgumentParser(description='Diagram-aligned MySQL electronics catalogue pipeline')
    parser.add_argument('command',choices=['sample','collect','validate','db-check','db-init','import-mysql','validate-mysql'])
    parser.add_argument('--per-category',type=int,default=20)
    args=parser.parse_args()
    if not 1<=args.per_category<=30:parser.error('per-category must be between 1 and 30')
    if args.command in ['sample','collect']:
        if args.command=='collect' and not (ROOT/'data/sample/validation_report.json').exists():
            parser.error('Run sample and review its report before collect')
        result=prepare(1 if args.command=='sample' else args.per_category,sample=args.command=='sample')
    elif args.command=='validate':
        result=validate(load_json(ROOT/'data/normalized/products.json',[]),load_json(ROOT/'data/normalized/provenance.json',[]),args.per_category)
    else:
        from crawler.database import importer
        if args.command=='db-check':result=importer.check_connection()
        elif args.command=='db-init':result=importer.initialize()
        elif args.command=='import-mysql':result=importer.import_products(load_json(ROOT/'data/normalized/products.json',[]))
        else:result=importer.validate_database()
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Do not print raw connection exceptions which could reveal configuration.
        if type(exc).__module__.startswith('mysql'):
            print('MySQL operation failed. Verify .env credentials, server and database privileges.',file=sys.stderr)
        else:print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        sys.exit(1)

"""Resumable retailer catalogue; isolated files and explicit separate database."""
import argparse
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib.parse import urljoin,urlparse

import requests
from Model.application.config.brands import canonical_brand
from crawler.config.settings import ROOT,CATEGORIES,database_options
from crawler.storage.files import load_json,save_json
from crawler.sources.retailer_sample import PublicClient
from crawler.sources.retailers import parse_product
from crawler.media.images import validate_image

FOLDER=ROOT/'data/retailer_catalog'
DATABASE='ecommerce_vn_retailer_demo'
SEEDS={
 'Smartphone':'https://cellphones.com.vn/mobile.html',
 'Laptop':'https://cellphones.com.vn/laptop.html',
 'Tablet':'https://cellphones.com.vn/tablet.html',
 'Headphones':'https://cellphones.com.vn/thiet-bi-am-thanh/tai-nghe.html',
 'Smartwatch':'https://cellphones.com.vn/do-choi-cong-nghe.html',
}

class ProductLinks(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.all_links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):
            self.all_links.append(attrs['href'])
            classes=attrs.get('class','')
            path=urlparse(attrs['href']).path
            if ('product__link' in classes or 'block h-fit w-full' in classes) and path.count('/')==1 and path.endswith('.html'):
                self.links.append(attrs['href'])

class FptWatchLinks(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);href=attrs.get('href','')
        if tag=='a' and attrs.get('title') and href.startswith('/smartwatch/') and not urlparse(href).query:
            self.links.append(urljoin('https://fptshop.com.vn',href))

def discover(client):
    listing=load_json(FOLDER/'listing_manifest.json',{})
    for category,url in SEEDS.items():
        if category in listing:
            listing[category]['product_urls']=[x for x in listing[category]['product_urls']
                if (urlparse(x).path.count('/')==1 or urlparse(x).hostname=='fptshop.com.vn')
                and x not in SEEDS.values()]
        if len(listing.get(category,{}).get('product_urls',[]))>=30:continue
        response=client.get(url);parser=ProductLinks();parser.feed(response.text)
        urls=list(dict.fromkeys(urljoin(url,x).split('#')[0] for x in parser.links))
        # Ordinary SEO product paths only; no filtered/search/API endpoints.
        urls=[x for x in urls if urlparse(x).hostname=='cellphones.com.vn' and not urlparse(x).query]
        prefix=urlparse(url).path.removesuffix('.html')+'/'
        subpages=list(dict.fromkeys(urljoin(url,x) for x in parser.all_links
            if urlparse(urljoin(url,x)).path.startswith(prefix)
            and urlparse(urljoin(url,x)).path.endswith('.html') and not urlparse(urljoin(url,x)).query))
        preferred=['apple','samsung','huawei','xiaomi','sony','jbl','garmin','amazfit','lenovo','asus']
        subpages.sort(key=lambda x: next((i for i,k in enumerate(preferred) if k in x),len(preferred)))
        explored=[]
        for subpage in subpages[:8]:
            if len(urls)>=35:break
            r=client.get(subpage);sub=ProductLinks();sub.feed(r.text)
            urls=list(dict.fromkeys(urls+[urljoin(subpage,x).split('#')[0] for x in sub.links
                if urlparse(urljoin(subpage,x)).hostname=='cellphones.com.vn'
                and not urlparse(urljoin(subpage,x)).query]))
            explored.append(subpage)
        if category=='Smartwatch' and len(urls)<35:
            fallback='https://fptshop.com.vn/smartwatch'
            response=client.get(fallback);fpt=FptWatchLinks();fpt.feed(response.text)
            urls=list(dict.fromkeys(urls+fpt.links));explored.append(fallback)
        listing[category]=dict(listing_url=url,additional_listing_urls=explored,product_urls=urls)
        save_json(FOLDER/'listing_manifest.json',listing)
        print(f'Discovered {category}: {len(urls)} product links',flush=True)
    return listing

def key_for(record):return record['provider']+':'+record['source_id']

def category_matches_name(category,name):
    title=name.strip().casefold()
    if category=='Smartwatch':
        return not title.startswith(('vòng đeo','nhẫn ','dây đeo','dây ','ốp ','kính ')) and not any(x in title for x in ['mi band','smart band','huawei band'])
    return True

def product_name_key(category,name):
    title=name.strip().casefold()
    if category=='Smartwatch':
        for phrase in ['đồng hồ thông minh','đồng hồ','dây cao su','silicone']:
            title=title.replace(phrase,' ')
        title=re.sub(r'\bgt\s+(\d)',r'gt\1',title)
    return ' '.join(title.split())

def download_images(client,record,article_id):
    entries=[];seen=set()
    for url in record['image_urls'][:3]:
        response=client.get(url);metadata=validate_image(response.content)
        if metadata['sha256'] in seen:continue
        seen.add(metadata['sha256'])
        suffix={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}.get(metadata['format'])
        if suffix is None:continue
        image_file=FOLDER/'images'/(metadata['sha256']+suffix)
        image_file.parent.mkdir(parents=True,exist_ok=True)
        if not image_file.exists():image_file.write_bytes(response.content)
        entries.append(dict(articleID=article_id,provider=record['provider'],source_id=record['source_id'],
            source_url=record['source_url'],image_url=url,local_path=image_file.relative_to(ROOT).as_posix(),
            rights_status=record['rights_status'],use_scope=record['use_scope'],**metadata))
    if not entries:raise ValueError('No valid product image; exclude incomplete product')
    return entries

def collect(per_category=20):
    FOLDER.mkdir(parents=True,exist_ok=True)
    client=PublicClient();listing=discover(client)
    keys=load_json(FOLDER/'product_key_map.json',{})
    if len(keys.values())!=len(set(keys.values())):raise ValueError('Duplicate registry IDs')
    checkpoint=load_json(FOLDER/'checkpoint.json',{})
    failures=load_json(FOLDER/'failures.json',[])
    products=[];provenance=[];images=[];counts=Counter();seen_names=set()
    for category in CATEGORIES:
        for url in listing.get(category,{}).get('product_urls',[]):
            if counts[category]>=per_category:break
            try:
                cached=checkpoint.get(url)
                from_cache=bool(cached and all((ROOT/e['local_path']).is_file() for e in cached['images']))
                if from_cache:
                    record=cached['record'];entries=cached['images'];article_id=cached['product']['articleID']
                else:
                    response=client.get(url);record=parse_product(response.text,url)
                    if record['currency']!='VND':raise ValueError('Expected a source VND offer')
                    source_key=key_for(record)
                    article_id=keys.get(source_key,max(keys.values(),default=0)+1)
                    keys[source_key]=article_id
                    save_json(FOLDER/'product_key_map.json',keys)
                    entries=download_images(client,record,article_id)
                name=record['productName'].strip()
                if not category_matches_name(category,name):
                    raise ValueError('Source category includes a different device/accessory type; excluded')
                name_key=product_name_key(category,name)
                if name_key in seen_names:continue
                seen_names.add(name_key)
                product=dict(articleID=article_id,categoryID=CATEGORIES[category],productName=name,
                    brand=canonical_brand(record['brand']),description=record['description'],technicalSpecs=record['technicalSpecs'],
                    warrantyTerms=None,imagePath=entries[0]['local_path'],price=record['price'],currency='VND',
                    isActive=True,imageEmbedding=None,textEmbedding=None,representationUpdateAt=None)
                # Never infer stock or warranty from marketing prose.
                now=datetime.now(timezone.utc).isoformat()
                raw=dict(record,collected_at=cached['collected_at'] if from_cache else now)
                save_json(ROOT/'data/raw/retailers'/(sha256(url.encode()).hexdigest()[:20]+'.json'),raw)
                checkpoint[url]=dict(record=record,product=product,images=entries,collected_at=raw['collected_at'])
                save_json(FOLDER/'checkpoint.json',checkpoint)
                products.append(product);images.extend(entries);counts[category]+=1
                provenance.append(dict(articleID=article_id,category=category,**raw))
                print(f'{category} {counts[category]}/{per_category}: {name}',flush=True)
            except (ValueError,requests.RequestException,RuntimeError) as exc:
                failures.append(dict(url=url,category=category,reason=str(exc)))
                save_json(FOLDER/'failures.json',failures)
                print(f'Skipped {url}: {exc}',flush=True)
                if isinstance(exc,RuntimeError) and ('refused' in str(exc) or 'limited' in str(exc)):
                    raise
    save_json(FOLDER/'products.json',products)
    save_json(FOLDER/'provenance.json',provenance)
    save_json(FOLDER/'images_manifest.json',images)
    save_json(FOLDER/'source_policy_checks.json',[
        dict(host=h,status=status,url=url,robots_text=text)
        for h,(_,status,url,text) in client.policies.items()])
    report=validate(per_category)
    save_json(FOLDER/'validation_report.json',report)
    gallery()
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def validate(target=20):
    products=load_json(FOLDER/'products.json',[]);images=load_json(FOLDER/'images_manifest.json',[])
    provenance=load_json(FOLDER/'provenance.json',[])
    ids=[p['articleID'] for p in products];counts=Counter(p['categoryID'] for p in products)
    bad=[]
    for entry in images:
        path=ROOT/entry['local_path']
        if not path.is_file():bad.append(entry['local_path']);continue
        content=path.read_bytes()
        if validate_image(content)['sha256']!=entry['sha256']:bad.append(entry['local_path'])
    orphan_images=[e['local_path'] for e in images if e['articleID'] not in ids]
    owned_images={(e['articleID'],e['local_path']) for e in images}
    mismatches=[p['articleID'] for p in products if (p['articleID'],p['imagePath']) not in owned_images]
    return dict(products=len(products),category_counts={k:counts[v] for k,v in CATEGORIES.items()},
        shortfalls={k:max(0,target-counts[v]) for k,v in CATEGORIES.items()},
        products_with_main_image=sum(bool(p['imagePath']) and (ROOT/p['imagePath']).is_file() for p in products),
        products_with_source_price=sum(Decimal(p['price'])>0 and p['currency']=='VND' for p in products),
        downloaded_images=len(images),unique_image_bytes=len({e['sha256'] for e in images}),
        duplicate_product_ids=len(ids)-len(set(ids)),orphan_images=orphan_images,invalid_images=bad,
        main_image_ownership_mismatches=mismatches,
        provenance_matches=sorted(ids)==sorted(e['articleID'] for e in provenance),
        missing_brands=sum(not p['brand'] for p in products),missing_specs=sum(not p['technicalSpecs'] for p in products),
        embeddings_generated=False,source_prices='Product-page JSON-LD snapshots; not guaranteed future checkout prices')

def gallery():
    products=load_json(FOLDER/'products.json',[]);provenance={p['articleID']:p for p in load_json(FOLDER/'provenance.json',[])}
    cards=[];categories={v:k for k,v in CATEGORIES.items()}
    for p in products:
        category=categories[p['categoryID']];source=provenance[p['articleID']]['source_url']
        image=Path(p['imagePath']).relative_to(Path('data/retailer_catalog')).as_posix()
        price=f"{Decimal(p['price']):,.0f}".replace(',','.')+' ₫'
        cards.append('<article data-category="'+escape(category,quote=True)+'"><img loading="lazy" src="'+escape(image,quote=True)+'" alt="'+escape(p['productName'],quote=True)+'"><small>#'+str(p['articleID'])+' · '+escape(category)+'</small><h2>'+escape(p['productName'])+'</h2><strong>'+price+'</strong><p><a target="_blank" rel="noopener" href="'+escape(source,quote=True)+'">Xem nguồn sản phẩm</a></p></article>')
    options='<option value="">Tất cả nhóm</option>'+''.join('<option>'+escape(c)+'</option>' for c in CATEGORIES)
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Danh mục điện tử — ảnh và giá VND</title><style>body{font:16px system-ui,sans-serif;margin:0;background:#f4f6fa;color:#17243b}header{padding:32px max(24px,5vw);background:#152c52;color:white}header p{max-width:850px;line-height:1.6}.controls{padding:24px max(24px,5vw);display:flex;gap:12px;flex-wrap:wrap}input,select{padding:12px;border:1px solid #bdc8d8;border-radius:8px;font:inherit}input{flex:1;min-width:220px}main{padding:0 max(24px,5vw) 40px;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}article{background:white;border:1px solid #dbe2ec;border-radius:12px;padding:20px}article[hidden]{display:none}img{width:100%;height:220px;object-fit:contain}h2{font-size:17px;line-height:1.5}strong{color:#ae1833;font-size:20px}small{color:#53637a}a{color:#2159a1}</style><header><h1>Danh mục sản phẩm điện tử</h1><p>Ảnh cục bộ, tên và giá VND được thu thập từ cùng trang sản phẩm. Giá là bản ghi tại thời điểm thu thập, có thể khác ưu đãi hoặc giá hiện tại. Bộ dữ liệu này độc lập với bộ 100 sản phẩm cũ.</p><span id="count"></span></header><div class="controls"><input id="search" placeholder="Tìm theo tên sản phẩm" aria-label="Tìm sản phẩm"><select id="category" aria-label="Chọn nhóm sản phẩm">'''+options+'''</select></div><main>'''+''.join(cards)+'''</main><script>const q=document.querySelector('#search'),c=document.querySelector('#category'),cards=[...document.querySelectorAll('article')];function filter(){let n=0;for(const a of cards){a.hidden=!!((c.value&&a.dataset.category!==c.value)||!a.querySelector('h2').textContent.toLocaleLowerCase('vi').includes(q.value.toLocaleLowerCase('vi')));if(!a.hidden)n++}document.querySelector('#count').textContent=n+' sản phẩm'}q.addEventListener('input',filter);c.addEventListener('change',filter);filter()</script></html>'''
    (FOLDER/'index.html').write_text(html,encoding='utf-8')

def import_catalog(database=DATABASE):
    from crawler.database import importer
    if database==database_options()['database']:
        raise ValueError('Retailer database must differ from the original .env database')
    report=validate()
    if (not report['products'] or any(report['shortfalls'].values())
        or report['duplicate_product_ids'] or report['invalid_images']
        or report['orphan_images'] or report['main_image_ownership_mismatches']
        or not report['provenance_matches']
        or report['products_with_main_image']!=report['products']
        or report['products_with_source_price']!=report['products']):
        raise ValueError('Catalogue validation failed')
    options=database_options();options.pop('database')
    import mysql.connector
    with mysql.connector.connect(**options) as connection:
        cursor=connection.cursor()
        cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=%s',(database,))
        tables={x[0].lower() for x in cursor.fetchall()}
    marker=load_json(FOLDER/'database_manifest.json',{})
    if not tables:
        importer.initialize(database)
        save_json(FOLDER/'database_manifest.json',dict(database=database,created_by='retailer_catalog'))
    elif tables!={'products','categories'} or marker.get('database')!=database:
        raise RuntimeError('Target already contains unmanaged data; choose a new database name')
    result=importer.import_products(load_json(FOLDER/'products.json'),database)
    result.update(database=database,validation=importer.validate_database(database))
    save_json(FOLDER/'mysql_validation_report.json',result)
    print(json.dumps(result,indent=2))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['collect','validate','gallery','import-mysql'])
    parser.add_argument('--per-category',type=int,default=20)
    parser.add_argument('--database',default=DATABASE)
    args=parser.parse_args()
    if not 1<=args.per_category<=30:parser.error('Choose 1–30 products per category')
    if args.command=='collect':collect(args.per_category)
    elif args.command=='validate':print(json.dumps(validate(args.per_category),indent=2))
    elif args.command=='gallery':gallery()
    else:import_catalog(args.database)

if __name__=='__main__':main()

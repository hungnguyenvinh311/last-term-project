"""Collect a small, read-only retailer pilot before choosing a final catalogue."""
from datetime import datetime,timezone
from hashlib import sha256
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import json
import time
import requests
from crawler.config.settings import ROOT
from crawler.media.images import validate_image
from crawler.sources.retailers import parse_product
from crawler.storage.files import save_json

URLS=[
 'https://cellphones.com.vn/dien-thoai-samsung-galaxy-s26-ultra.html',
 'https://fptshop.com.vn/dien-thoai/nubia-a76',
 'https://cellphones.com.vn/dien-thoai-honor-600.html',
 'https://cellphones.com.vn/dien-thoai-honor-600s.html',
 'https://cellphones.com.vn/xiaomi-redmi-note-14-pro-plus.html',
]

class PublicClient:
    def __init__(self):
        self.session=requests.Session()
        self.session.headers['User-Agent']='ElectronicsCourseworkDataset/1.0 (small educational sample)'
        self.policies={};self.last_request=0
    def request(self,url):
        time.sleep(max(0,2-(time.monotonic()-self.last_request)))
        r=self.session.get(url,timeout=(10,30),verify=requests.certs.where())
        self.last_request=time.monotonic()
        # No bypass/retry against access controls or rate limiting.
        if r.status_code in (401,403,429):raise RuntimeError('Site refused or limited access: stop this source')
        return r
    def get(self,url):
        u=urlparse(url)
        if u.scheme!='https':raise ValueError('HTTPS required')
        if u.hostname not in self.policies:
            robots_url=f'https://{u.hostname}/robots.txt'
            r=self.request(robots_url)
            if r.status_code not in (200,404):r.raise_for_status()
            parser=RobotFileParser();parser.parse(r.text.splitlines() if r.status_code==200 else [])
            self.policies[u.hostname]=(parser,r.status_code,robots_url,r.text if r.status_code==200 else '')
        if not self.policies[u.hostname][0].can_fetch(self.session.headers['User-Agent'],url):
            raise RuntimeError('Requested path is disallowed by robots.txt')
        r=self.request(url);r.raise_for_status();return r

def main():
    client=PublicClient();products=[];images=[];failures=[]
    folder=ROOT/'data/retailer_sample';folder.mkdir(parents=True,exist_ok=True)
    for url in URLS:
        try:
            r=client.get(url)
            product=parse_product(r.text,url)
            product['collected_at']=datetime.now(timezone.utc).isoformat()
            product['local_images']=[]
            # Keep a clean product-only raw extract; never save reviews or customer names.
            rawkey=sha256(url.encode()).hexdigest()[:20]
            save_json(ROOT/'data/raw/retailers'/f'{rawkey}.json',product)
            for image_url in product['image_urls'][:3]:
                try:
                    img=client.get(image_url);info=validate_image(img.content)
                    suffix={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}.get(info['format'])
                    if not suffix:raise ValueError('Unsupported image format')
                    dest=folder/'images'/(info['sha256']+suffix);dest.parent.mkdir(exist_ok=True)
                    if not dest.exists():dest.write_bytes(img.content)
                    rel=dest.relative_to(ROOT).as_posix()
                    product['local_images'].append(rel)
                    images.append(dict(source_id=product['source_id'],provider=product['provider'],
                        source_url=url,image_url=image_url,local_path=rel,**info,
                        rights_status='Retailer copyright; no open licence claimed',use_scope='Local coursework as requested'))
                except (requests.RequestException,ValueError,RuntimeError) as e:
                    failures.append(dict(url=image_url,reason=str(e)))
            products.append(product)
        except (requests.RequestException,ValueError,RuntimeError) as e:
            failures.append(dict(url=url,reason=str(e)))
    policies=[dict(host=host,status=status,url=url,robots_text=text) for host,(_,status,url,text) in client.policies.items()]
    save_json(folder/'products.json',products);save_json(folder/'images_manifest.json',images)
    save_json(folder/'source_policy_checks.json',policies)
    report=dict(products=len(products),products_with_price=sum(bool(p['price']) for p in products),
        products_with_local_image=sum(bool(p['local_images']) for p in products),downloaded_images=len(images),
        failures=failures,database_changed=False,open_license_asserted=False)
    save_json(folder/'validation_report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

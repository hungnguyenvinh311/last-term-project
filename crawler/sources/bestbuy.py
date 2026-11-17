import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser
from crawler.config.settings import ROOT
from crawler.storage.files import save_json

BASE='https://raw.githubusercontent.com/BestBuyAPIs/open-data-set/master/'
DATA_URL=BASE+'products.json.gz'
LICENSE_URL=BASE+'LICENSE'
PROVIDER='bestbuy_open_data'

def fetch_snapshot():
    """Download a licensed historical snapshot; no retailer HTML or image crawl."""
    import requests
    session=requests.Session()
    session.headers['User-Agent']='ElectronicsCourseworkDataset/1.0 (educational; bounded requests)'
    def get(url, allow_missing=False):
        for attempt in range(3):
            response=session.get(url,timeout=(10,45),verify=requests.certs.where())
            if response.status_code==429:
                raise RuntimeError('Source rate limit: stop and retry later; no bypass')
            if allow_missing and response.status_code==404:
                return response
            if response.status_code>=500 and attempt<2:
                time.sleep(2**attempt);continue
            response.raise_for_status();time.sleep(1.5);return response
        raise RuntimeError('Source request failed')
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    target=raw/'products.json.gz'
    if target.exists(): return json.loads(gzip.decompress(target.read_bytes()))
    robots=get('https://raw.githubusercontent.com/robots.txt',allow_missing=True)
    parser=RobotFileParser();parser.parse(robots.text.splitlines() if robots.status_code==200 else [])
    if not parser.can_fetch(session.headers['User-Agent'],DATA_URL):
        raise RuntimeError('robots.txt does not permit dataset acquisition')
    license_response=get(LICENSE_URL)
    if not license_response.text.startswith('CC0 1.0 Universal'):
        raise RuntimeError('Unexpected licence; review before downloading')
    response=get(DATA_URL)
    data=json.loads(gzip.decompress(response.content))
    if not isinstance(data,list):raise ValueError('Expected product array')
    target.write_bytes(response.content)
    (raw/'BESTBUY_LICENSE.txt').write_text(license_response.text,encoding='utf-8')
    (raw/'github_robots.txt').write_text(robots.text,encoding='utf-8')
    save_json(raw/'snapshot_manifest.json',dict(provider=PROVIDER,url=DATA_URL,
        retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(response.content).hexdigest(),
        records=len(data),license='CC0-1.0',robots_status=robots.status_code,price_basis='Historical source price; not a current live offer',
        currency_basis='USD, Best Buy US source catalogue',image_rights='External image bytes not included in this repository licence check'))
    return data

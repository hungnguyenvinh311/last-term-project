from functools import lru_cache
import hashlib
import json
from Model.application.config.settings import ROOT

MANIFEST=ROOT/'data/retailer_catalog/embedding_manifest.json'

@lru_cache(maxsize=2048)
def _image_hash(path,size,mtime,ctime):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hash(product):
    path=ROOT/(product.get('imagePath') or '_missing')
    stat=path.stat() if path.is_file() else None
    image=_image_hash(path,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns) if stat else None
    data={k:product.get(k) for k in ('productName','brand','description','technicalSpecs')}
    return hashlib.sha256(json.dumps([data,image],sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def metadata():
    try: return json.loads(MANIFEST.read_text(encoding='utf-8'))
    except (OSError,ValueError): return {}

def valid(product,manifest,identity):
    record=manifest.get('products',{}).get(str(product['articleID']),{})
    return manifest.get('identity')==identity and record.get('source_hash')==source_hash(product)

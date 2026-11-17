"""Explicit real-model preparation; never generates synthetic vectors."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from Model.application.config.settings import ROOT
from DAO.application.dao.connection import Database
from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
from Model.application.ai.MultimodalEmbedderService import MultimodalEmbedderService
from Model.application.retrieval.representations import MANIFEST,metadata,source_hash
from crawler.storage.files import save_json
from Model.application.ai.product_caption import product_caption

CATEGORY={1:'smartphone mobile phone',2:'laptop computer',3:'tablet computer',4:'headphones earbuds',5:'smartwatch wrist watch'}

def prepare():
    import numpy as np
    products=ProductDAOImpl(Database());encoder=MultimodalEmbedderService();encoder.load()
    report=metadata()
    if report.get('identity')!=encoder.identity: report={'identity':encoder.identity,'products':{}}
    # Hash actual model state once: a model tag alone is insufficient provenance.
    digest=hashlib.sha256()
    for name,tensor in encoder.model.state_dict().items():
        digest.update(name.encode());digest.update(tensor.detach().cpu().numpy().tobytes())
    if report.get('weights_sha256') and report['weights_sha256']!=digest.hexdigest(): report['products']={}
    report['weights_sha256']=digest.hexdigest()
    report['preprocessing']=str(encoder.preprocess);report['normalization']='L2';report['failures']=[]
    for p in products.findActive():
        key=str(p['articleID']);fingerprint=source_hash(p)
        old=report['products'].get(key,{})
        if old.get('source_hash')==fingerprint and p.get('imageEmbedding') and p.get('textEmbedding'): continue
        try:
            with Image.open(ROOT/p['imagePath']) as image: image_vector=encoder.encodeImage(image.convert('RGB'))
            text=product_caption(p)
            text_vector=encoder.encodeText(text)
            if len(image_vector)!=len(text_vector) or not np.isfinite(image_vector+text_vector).all(): raise ValueError('Invalid embedding')
            products.saveRepresentation(p['articleID'],image_vector,text_vector)
            report['products'][key]={'source_hash':fingerprint,'dimension':len(image_vector),'updatedAt':datetime.now(timezone.utc).isoformat()}
            print(f'Encoded {key}: {p["productName"]}',flush=True)
        except Exception as exc:
            report['products'].pop(key,None);report['failures'].append({'articleID':p['articleID'],'errorType':type(exc).__name__})
        save_json(MANIFEST,report)
    save_json(MANIFEST,report)
    print(f"Prepared {len(report['products'])} products; failures: {len(report['failures'])}")

if __name__=='__main__': prepare()

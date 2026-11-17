"""Real encoder smoke checks; not a business-relevance benchmark."""
import sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from bootstrap import create_app
from crawler.storage.files import save_json
from Model.application.retrieval.representations import metadata
from Model.application.retrieval.CandidateRetriever import cosine
from PIL import Image

def run():
    from Model.application.ai.IntentExtractorService import IntentExtractorService
    app=create_app(overrides={'intent':IntentExtractorService()});s=app.state.services;products=s['products'].findActive();encoder=s['embedder']
    record={'identity':encoder.identity,'products':len(products),'manifestProducts':len(metadata().get('products',{})),'cases':[]}
    assert record['manifestProducts']==100
    start=time.perf_counter();vector=encoder.encodeText('Samsung smartphone mobile phone');record['encoder_load_and_first_text_seconds']=time.perf_counter()-start
    assert len(vector)==512
    # Read-only image retrieval: no query history writes to the demo DB.
    from Model.application.dto.SearchCriteria import SearchCriteria
    for cid in range(1,6):
        source=next(p for p in products if p['categoryID']==cid)
        start=time.perf_counter()
        with Image.open(ROOT/source['imagePath']) as image: query=encoder.encodeImage(image.convert('RGB'))
        self_similarity=cosine(query,source['imageEmbedding'])
        assert self_similarity is not None and self_similarity>0.999
        ranked=s['search'].ranking.rankForQuery(s['search'].retriever.retrieveForQuery(SearchCriteria(),query,'image'),SearchCriteria())
        assert ranked and any(p['articleID']==source['articleID'] for p in ranked[:5])
        rec=s['recommendation'].recommendForProduct(source['articleID'])
        assert len(rec['products'])==8 and all(p['articleID']!=source['articleID'] and p['categoryID']==cid for p in rec['products'])
        assert rec['fallback'] is False
        record['cases'].append({'categoryID':cid,'sourceArticleID':source['articleID'],'self_image_cosine':self_similarity,'self_image_top5':True,'firstResult':ranked[0]['articleID'],'recommendations':8,'fallback':False,'seconds':time.perf_counter()-start})
    criteria=s['search'].intent.extractCriteria('điện thoại Samsung dưới 40 triệu')
    rows=s['search'].retriever.retrieveForQuery(criteria,vector,'text')
    assert rows and all(p['categoryID']==1 and float(p['price'])<=40_000_000 for p in rows)
    record['status']='passed';record['limitation']='Self-image checks establish pipeline consistency, not real-world Recall@K or recommendation usefulness.'
    save_json(ROOT/'data/test_runs/real_ai_smoke.json',record)
    print('Real encoder smoke passed for all five categories; report saved.')

if __name__=='__main__': run()

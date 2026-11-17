from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from Model.application.ai.IntentExtractorService import IntentExtractorService,canonical_query
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.normalization import matches
from Model.application.service.SearchService import SearchService
from Model.application.context.SearchSessionService import SearchSessionService
from Model.application.retrieval.SoftReranker import SoftReranker
from Model.application.retrieval import representations

def product(name, specs=None):
    return dict(articleID=1,productName=name,technicalSpecs=specs or {},categoryID=1,brand='Samsung',price=100,isActive=True)

@pytest.mark.parametrize('query,good,bad',[
    ('Samsung màu đen','Samsung Black','Samsung White'),
    ('điện thoại màu xanh dương','Phone Blue','Phone Green'),
    ('phone màu trắng','Phone White','Phone Black'),
    ('phone màu đỏ','Phone Red','Phone Black'),
])
def test_explicit_color_is_hard_evidence(query,good,bad):
    criteria=IntentExtractorService().extractCriteria(query)
    assert matches(product(good),criteria)
    assert not matches(product(bad),criteria)
    assert not matches(product('Unknown colour'),criteria)
    assert any(t.startswith('color:') for t in criteria.requiredTerms)
    assert criteria.requiredTerms[-1][6:] in canonical_query(criteria)

def test_budget_den_is_not_black_and_negative_color():
    c=IntentExtractorService().extractCriteria('điện thoại đến 10 triệu')
    assert not any(t.startswith('color:') for t in c.requiredTerms)
    c=IntentExtractorService().extractCriteria('phone không màu đen')
    assert 'color:black' not in c.requiredTerms
    assert not matches(product('Phone Black'),c)
    assert matches(product('Phone White'),c)

def test_color_from_specs_and_context_replacement():
    c=IntentExtractorService().extractCriteria('điện thoại màu đen')
    assert matches(product('Phone',{'Màu sắc':'Black'}),c)
    assert not matches(product('Phone',{'Bộ nhớ':'Lên đến 256 GB'}),c)
    ctx=SearchSessionService()
    ctx.mergeCriteria('a',c)
    c=ctx.mergeCriteria('a',IntentExtractorService().extractCriteria('màu trắng'))
    assert 'color:black' not in c.requiredTerms and 'color:white' in c.requiredTerms

def test_cache_reuses_inference_without_cross_filter_mutation():
    calls={'intent':0,'vector':0}
    class Intent:
        def extractCriteria(self,text):
            calls['intent']+=1
            return SearchCriteria(text=text)
    class Encoder:
        identity='test'
        def encodeText(self,text):
            calls['vector']+=1
            return [1,0]
    service=SearchService(Intent(),None,None,Encoder(),None,None,None,None,None)
    c=service._criteria('phone');service._filters(c,'Samsung',1)
    assert service._criteria('phone').brand is None
    first=service._text_vector('phone');first[0]=999
    assert service._text_vector('phone')==[1,0]
    assert calls=={'intent':1,'vector':1}
    service._criteria('laptop');service._text_vector('laptop')
    assert calls=={'intent':2,'vector':2}
    service._cache={k:(0,v[1]) for k,v in service._cache.items()}
    service._criteria('phone')
    assert calls['intent']==3

def test_failed_inference_is_not_cached():
    service=SearchService(None,None,None,None,None,None,None,None,None)
    calls=[]
    def failure(): calls.append(1);raise RuntimeError('offline')
    for _ in range(2):
        with pytest.raises(RuntimeError):service._reuse('image','a',failure)
    assert len(calls)==2

def test_source_hash_cache_invalidates_on_image_change(tmp_path,monkeypatch):
    monkeypatch.setattr(representations,'ROOT',tmp_path)
    image=tmp_path/'image.bin';image.write_bytes(b'first')
    p=product('Phone');p['imagePath']='image.bin'
    a=representations.source_hash(p)
    assert representations.source_hash(p)==a
    image.write_bytes(b'different')
    assert representations.source_hash(p)!=a
    image.unlink()
    assert representations.source_hash(p)!=a

def test_rank_components_reconstruct_score_and_ties_are_stable():
    rows=[dict(articleID=2,similarity=.8,textSimilarity=.4,lexical=.5),dict(articleID=1,similarity=.8,textSimilarity=.4,lexical=.5)]
    ranked=SoftReranker('test').rankForQuery(rows,SearchCriteria())
    assert [p['articleID'] for p in ranked]==[1,2]
    for p in ranked:
        d=p['matchDetails']
        assert p['score']==pytest.approx(.6*d['embedding']+.2*d['text']+.2*d['keyword'])
        assert d['metric']=='cosine' and d['rankScore']==p['score']

def test_image_text_filters_cache_and_evidence_end_to_end(monkeypatch):
    from PIL import Image
    from io import BytesIO
    from Model.application.service import SearchService as module
    from Model.application.retrieval.CandidateRetriever import CandidateRetriever
    from Model.application.retrieval import CandidateRetriever as retrieval_module
    calls={'image':0,'text':0,'intent':0}
    rows=[dict(product('Samsung Black'),imageEmbedding=[1,0],textEmbedding=[1,0]),
          dict(product('Samsung White'),articleID=2,imageEmbedding=[.9,.1],textEmbedding=[0,1]),
          dict(product('Samsung White'),articleID=3,brand='Other',imageEmbedding=[1,0],textEmbedding=[1,0])]
    class Encoder:
        identity='test'
        def encodeImage(self,image): calls['image']+=1;return [1,0]
        def encodeText(self,text): calls['text']+=1;return [0,1]
    class Intent:
        def extractCriteria(self,text): calls['intent']+=1;return IntentExtractorService().extractCriteria(text)
    class Products:
        def findByRepresentation(self,criteria):return [deepcopy(p) for p in rows if matches(p,criteria)]
    class Media:
        def validateImage(self,content):return Image.open(BytesIO(content)).convert('RGB')
        def saveUpload(self,*a):return 'test/image.png'
    class Queries:
        saved=[]
        def saveWithResults(self,*args): self.saved.append(args);return len(self.saved)
    manifest={'identity':'test','products':{'1':{}}}
    monkeypatch.setattr(module,'metadata',lambda:manifest)
    monkeypatch.setattr(retrieval_module,'metadata',lambda:manifest)
    monkeypatch.setattr(retrieval_module,'valid',lambda *a:True)
    encoder=Encoder();queries=Queries()
    service=SearchService(Intent(),None,None,encoder,None,CandidateRetriever(Products(),encoder),SoftReranker('test'),queries,Media())
    buf=BytesIO();Image.new('RGB',(10,10)).save(buf,format='PNG');content=buf.getvalue()
    for _ in range(2):
        response=service.searchImage(content,text='phone màu trắng',brand='Samsung',categoryID=1)
        assert [p['articleID'] for p in response['products']]==[2]
        assert response['products'][0]['matchDetails']['text']==1
        assert 'imageEmbedding' not in response['products'][0]
    assert calls=={'image':1,'text':1,'intent':1}
    # Fresh retrieval still honours changed stock: cached inference is not cached results.
    rows[1]['isActive']=False
    assert service.searchImage(content,text='phone màu trắng',brand='Samsung')['products']==[]
    assert len(queries.saved)==3

def test_concurrent_same_query_is_coalesced_and_unrelated_query_can_run():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    service=SearchService(None,None,None,None,None,None,None,None,None)
    started=Event();release=Event();calls=[]
    def slow():
        calls.append(1);started.set();assert release.wait(3);return [1]
    with ThreadPoolExecutor(max_workers=3) as pool:
        first=pool.submit(service._reuse,'a','key',slow)
        assert started.wait(2)
        second=pool.submit(service._reuse,'a','key',slow)
        independent=pool.submit(service._reuse,'b','key',lambda:[2])
        assert independent.result(timeout=1)==[2]
        release.set()
        assert first.result()==second.result()==[1]
    assert calls==[1]

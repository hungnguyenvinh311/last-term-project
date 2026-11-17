from io import BytesIO
from types import SimpleNamespace
from PIL import Image
import pytest
from Model.application.ai.detection_categories import category_for_label
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.retrieval.CandidateRetriever import CandidateRetriever
from Model.application.retrieval.SoftReranker import SoftReranker
from Model.application.service.SearchService import SearchService
from Model.application.errors import DomainError

@pytest.fixture
def image_search(monkeypatch):
    import importlib
    module=importlib.import_module('Model.application.service.SearchService')
    retrieval=importlib.import_module('Model.application.retrieval.CandidateRetriever')
    monkeypatch.setattr(module,'metadata',lambda:{'identity':'test'})
    monkeypatch.setattr(retrieval,'metadata',lambda:{'identity':'test'})
    monkeypatch.setattr(retrieval,'valid',lambda *args:True)
    rows=[dict(articleID=i,categoryID=category,productName=name,brand='Brand',price=100,isActive=True,
               imageEmbedding=vector,textEmbedding=vector) for i,category,name,vector in
          [(1,1,'Phone',[.9,.1]),(3,3,'Tablet',[.4,.9165]),(4,4,'Headphones',[1,0]),(5,5,'Watch',[.99,.01])]]
    class Products:
        # Intentionally overbroad, to exercise the retriever's final category guard.
        def findByRepresentation(self,criteria):return rows
    calls=[]
    class Encoder:
        identity='test'
        def encodeImage(self,image):calls.append(image.size);return [1,0]
        def encodeText(self,text):return [1,0]
    class Media:
        def validateImage(self,content):return Image.open(BytesIO(content)).convert('RGB')
        def saveUpload(self,*args):return 'test/image.png'
    saved=[]
    class Queries:
        def saveWithResults(self,*args):saved.append(args);return len(saved)
    detector=ObjectDetectorService()
    detector.detectProducts=lambda image:[dict(label=label,score=.8,region=region) for label,region in
        [('a tablet computer',[0,0,.5,.5]),('a mobile phone',[.5,0,1,.5]),('headphones',[0,.5,.5,1])]]
    encoder=Encoder();service=SearchService(IntentExtractorService(),None,detector,encoder,None,CandidateRetriever(Products(),encoder),SoftReranker('test'),Queries(),Media())
    buf=BytesIO();Image.new('RGB',(100,100)).save(buf,format='PNG')
    return SimpleNamespace(service=service,content=buf.getvalue(),rows=rows,calls=calls,saved=saved)

@pytest.mark.parametrize('label,category',[('a tablet computer',3),('a mobile phone',1),('a laptop computer',2),('headphones',4),('a smartwatch',5),('unknown object',None)])
def test_detection_category_mapping_is_stable(label,category):
    assert category_for_label(label)==category

def test_detection_exposes_category_for_each_of_three_objects(image_search):
    result=image_search.service.detectImageProducts(image_search.content)
    assert [r['categoryID'] for r in result['regions']]==[3,1,4]
    assert result['regions'][0]['label']=='a tablet computer'

@pytest.mark.parametrize('selected,expected',[(3,[3]),(1,[1]),(4,[4]),(5,[5])])
def test_selected_type_excludes_wrong_types_even_when_they_score_higher(image_search,selected,expected):
    f=image_search
    result=f.service.searchImage(f.content,region=[0,0,.5,.5],imageCategoryID=selected)
    assert [p['articleID'] for p in result['products']]==expected
    assert result['criteria']['categoryID']==selected
    assert result['imageSelection']['categoryID']==selected
    assert f.calls==[(50,50)]
    assert f.saved[0][2]['categoryID']==selected

def test_changing_category_reuses_crop_embedding_but_retrieves_new_type(image_search):
    f=image_search
    tablet=f.service.searchImage(f.content,region=[0,0,.5,.5],imageCategoryID=3)
    corrected=f.service.searchImage(f.content,region=[0,0,.5,.5],imageCategoryID=1)
    assert tablet['products'][0]['categoryID']==3 and corrected['products'][0]['categoryID']==1
    assert f.calls==[(50,50)]

def test_no_selected_type_results_never_falls_back_to_other_categories(image_search):
    f=image_search;f.rows[:]=[p for p in f.rows if p['categoryID']!=3]
    assert f.service.searchImage(f.content,region=[0,0,.5,.5],imageCategoryID=3)['products']==[]

@pytest.mark.parametrize('invalid',[0,6,-1,True,'3',3.5])
def test_invalid_image_category_rejected_before_inference(image_search,invalid):
    with pytest.raises(DomainError):image_search.service.searchImage(image_search.content,imageCategoryID=invalid)
    assert image_search.calls==[] and image_search.saved==[]

@pytest.mark.parametrize('params',[{'categoryID':1},{'text':'điện thoại'}])
def test_text_or_catalogue_category_conflict_is_visible_before_image_encoding(image_search,params):
    with pytest.raises(DomainError):image_search.service.searchImage(image_search.content,region=[0,0,.5,.5],imageCategoryID=3,**params)
    assert image_search.calls==[] and image_search.saved==[]

def test_full_image_can_have_an_explicit_category_without_a_crop(image_search):
    result=image_search.service.searchImage(image_search.content,imageCategoryID=3)
    assert [p['categoryID'] for p in result['products']]==[3]
    assert image_search.calls==[(100,100)]

def test_crop_without_any_resolved_category_requests_user_correction(image_search):
    with pytest.raises(DomainError,match='loại sản phẩm'):
        image_search.service.searchImage(image_search.content,region=[0,0,.5,.5])
    assert image_search.calls==[] and image_search.saved==[]

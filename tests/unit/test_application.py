import pytest
from PIL import Image
from Model.application.ai.IntentExtractorService import IntentExtractorService,canonical_query
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.context.SearchSessionService import SearchSessionService
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.normalization import matches
from Model.application.service.AccountService import hash_password,check_password
from Model.application.errors import DomainError
from Model.application.retrieval.CandidateRetriever import cosine

def test_electronics_constraints():
    c=IntentExtractorService().extractCriteria('điện thoại Samsung dưới 10 triệu RAM 8 GB không Xiaomi')
    assert c.categoryID==1 and c.brand=='samsung' and c.maxPrice==10_000_000
    assert c.specs=={'ram':{'value':8,'op':'eq','unit':'gb'}} and c.excludedTerms==['xiaomi']
    assert 'smartphone' in canonical_query(c)
    ranged=IntentExtractorService().extractCriteria('laptop từ 10 đến 20 triệu')
    assert ranged.minPrice==10_000_000 and ranged.maxPrice==20_000_000

def test_hard_specs_missing_is_not_a_match():
    p=dict(isActive=True,articleID=1,categoryID=1,brand='Samsung',price=5_000_000,productName='Phone',technicalSpecs={})
    c=SearchCriteria(specs={'ram':8})
    assert not matches(p,c)
    p['technicalSpecs']={'Dung lượng RAM':'8 GB'}
    assert matches(p,c)
    p['technicalSpecs']={'Dung lượng RAM':'18 GB'}
    assert not matches(p,c)

def test_context_isolation_reset_and_expiry():
    ctx=SearchSessionService(ttl=100)
    ctx.mergeCriteria('alice',SearchCriteria(categoryID=1,maxPrice=10_000_000))
    merged=ctx.mergeCriteria('alice',SearchCriteria(specs={'ram':8}))
    assert merged.categoryID==1 and merged.maxPrice==10_000_000 and merged.specs=={'ram':8}
    assert ctx.getOrCreate('bob')['criteria'].categoryID is None
    assert ctx.mergeCriteria('alice',SearchCriteria(categoryID=2)).maxPrice is None
    assert ctx.mergeCriteria('alice',SearchCriteria(),reset=True).categoryID is None
    ctx.ttl=-1
    assert ctx.getOrCreate('alice')['criteria'].specs=={}

def test_numeric_minimum_and_feature_key_is_not_evidence():
    criteria=IntentExtractorService().extractCriteria('điện thoại pin ít nhất 6000 mAh')
    p=dict(isActive=True,articleID=1,categoryID=1,brand='Samsung',price=5_000_000,productName='Phone',technicalSpecs={'Pin':'5000 mAh'})
    assert not matches(p,criteria)
    p['technicalSpecs']['Pin']='6500 mAh'
    assert matches(p,criteria)
    p['technicalSpecs']={'Chống ồn':'Không'}
    assert not matches(p,SearchCriteria(requiredTerms=['chong on']))

def test_crop_contract():
    detector=ObjectDetectorService();im=Image.new('RGB',(100,100))
    assert detector.cropRegion(im,[0,.2,.5,.8]).size==(50,60)
    for region in [[-1,0,1,1],[.5,0,.2,1],[0,0,1],['x',0,1,1]]:
        with pytest.raises(DomainError): detector.cropRegion(im,region)

def test_password_hash_and_vector_guard():
    encoded=hash_password('correct-long-password')
    assert check_password('correct-long-password',encoded)
    assert not check_password('incorrect-password',encoded)
    assert cosine([1,0],[1,0])==1
    assert cosine([1],[1,2]) is None
    assert cosine([0,0],[1,1]) is None
    assert cosine([float('nan')],[1]) is None

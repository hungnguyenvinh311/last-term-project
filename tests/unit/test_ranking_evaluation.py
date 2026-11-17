import math
from copy import deepcopy
import pytest
from Model.application.retrieval.RankingEvaluation import weighted_score,grid,metrics,tune,validate_cases
from Model.application.ai.IntentExtractorService import IntentExtractorService,canonical_query
from Model.application.normalization import matches

def case(identifier,split,truth):
    return {'caseID':identifier,'kind':'text','split':split,'groupID':identifier,'reviewed':True,
            'relevantArticleIDs':truth,'candidates':[{'articleID':1,'similarity':.1,'lexical':1},
                                                  {'articleID':2,'similarity':.9,'lexical':0}]}

def test_grid_is_valid_and_mode_specific():
    assert len(grid('text'))==21 and len(grid('image_text'))==231
    assert grid('image')==[(1,0,0)]
    for kind in ('text','image','image_text'):
        for weights in grid(kind):assert sum(weights)==pytest.approx(1) and min(weights)>=0
    assert all(w[1]==0 for w in grid('text'))

@pytest.mark.parametrize('weights',[(1,1,1),(-.1,.1,1),(float('nan'),0,1),(float('inf'),0,0),(1,0)])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):weighted_score({},weights)

def test_binary_metrics_order_and_shortlist_denominator():
    result=metrics([{'articleID':2,'similarity':.9},{'articleID':1,'similarity':.1}],{1},(1,0,0),5)
    assert result['recallAtK']==1 and result['precisionAtK']==.2 and result['mrrAtK']==.5
    assert result['ndcgAtK']==pytest.approx(1/math.log2(3)) and result['hitAt1']==0
    assert result['returned']==[2,1]

def test_missing_candidate_cannot_be_recovered_by_weights_and_no_answer():
    result=metrics([{'articleID':2,'similarity':1}],{1},(1,0,0),5)
    assert result['candidateRecall']==result['recallAtK']==result['ndcgAtK']==0
    assert metrics([],[],(1,0,0),5)['noAnswerCorrect']==1
    assert metrics([{'articleID':2,'similarity':1}],[],(1,0,0),5)['noAnswerCorrect']==0

def test_grid_selection_never_uses_test_labels():
    cases=[case('val','validation',[1]),case('held-out','test',[2])]
    original=tune(cases)
    changed=deepcopy(cases);changed[1]['relevantArticleIDs']=[1]
    alternate=tune(changed)
    assert original['text']['weights']==alternate['text']['weights']
    assert original['text']['selectedValidation']['ndcgAtK']==1
    assert original['text']['selectedTest']!=alternate['text']['selectedTest']

def test_review_and_group_leakage_guards():
    cases=[case('val','validation',[1]),case('held-out','test',[2])]
    cases[0]['reviewed']=False
    with pytest.raises(ValueError,match='review'):tune(cases)
    tune(cases,reviewed=False)
    cases[1]['groupID']='val'
    with pytest.raises(ValueError,match='leakage'):validate_cases(cases,reviewed=False)

def test_orange_is_a_hard_constraint_before_ranking():
    c=IntentExtractorService().extractCriteria('điện thoại màu cam')
    assert 'color:orange' in c.requiredTerms and 'orange' in canonical_query(c)
    p={'articleID':1,'isActive':True,'productName':'Phone Orange','categoryID':1,'technicalSpecs':{}}
    assert matches(p,c)
    p['productName']='Phone Blue'
    assert not matches(p,c)

def test_wireless_is_not_a_negative_condition():
    c=IntentExtractorService().extractCriteria('tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC)')
    assert 'day' not in c.excludedTerms
    p={'articleID':66,'isActive':True,'productName':'Tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC)',
       'categoryID':4,'brand':'Xiaomi','technicalSpecs':{}}
    assert matches(p,c)

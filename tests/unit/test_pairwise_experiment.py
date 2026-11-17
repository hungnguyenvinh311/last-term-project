from collections import Counter
from PIL import Image
import pytest
from scripts.pairwise_image_search import representatives,pair_specs,compose_pair,located_in_panel,detection_for_target,search_summary

def products():
    return [dict(articleID=c,categoryID=c,productName=str(c),imagePath=f'{c}.png',isActive=True) for c in range(1,6)]

def test_pairs_cover_every_other_category_exactly_once():
    pairs=pair_specs(products())
    assert len(pairs)==10
    assert len({tuple(sorted((a['categoryID'],b['categoryID']))) for a,b in pairs})==10
    assert Counter(p['categoryID'] for pair in pairs for p in pair)=={c:4 for c in range(1,6)}

def test_representatives_are_deterministic_without_special_product_ids():
    rows=products()+[dict(articleID=99,categoryID=1,imagePath='99.png',isActive=True)]
    assert [p['articleID'] for p in representatives(list(reversed(rows)))]==[1,2,3,4,5]
    with pytest.raises(ValueError):representatives(rows[1:4])

def test_query_composition_and_known_regions_are_separate_from_annotations(tmp_path):
    a,b=products()[:2]
    Image.new('RGB',(40,40),'red').save(tmp_path/a['imagePath'])
    Image.new('RGB',(40,40),'blue').save(tmp_path/b['imagePath'])
    before=(tmp_path/a['imagePath']).read_bytes()
    canvas,targets=compose_pair(a,b,root=tmp_path,panel=100)
    assert canvas.size==(200,100) and canvas.getpixel((50,50))==(255,0,0) and canvas.getpixel((150,50))==(0,0,255)
    assert targets[0]['panelRegion']==[0,0,.5,1] and targets[1]['panelRegion']==[.5,0,1,1]
    assert targets[0]['sourceImageRegion'][2]<=.5 and targets[1]['sourceImageRegion'][0]>=.5
    assert (tmp_path/a['imagePath']).read_bytes()==before

def test_wrong_strongest_label_is_not_replaced_with_known_correct_answer():
    target={'categoryID':3,'panelRegion':[0,0,.5,1]}
    wrong={'categoryID':1,'label':'a mobile phone','score':.95,'region':[.1,.1,.4,.8]}
    correct={'categoryID':3,'label':'a tablet computer','score':.7,'region':[.1,.1,.4,.8]}
    strongest,best=detection_for_target([wrong,correct],target)
    assert strongest['categoryID']==1 and best['categoryID']==3
    assert strongest['detectorIndex']==1 and best['detectorIndex']==2

@pytest.mark.parametrize('region',[[0,0,1,1],[.6,.1,.9,.9],[.4,.1,.9,.9],[0,0,0,.5],[-.1,0,.2,.3],[0,0,float('nan'),.3]])
def test_other_panel_and_ambiguous_or_invalid_boxes_are_not_matched(region):
    assert not located_in_panel({'region':region},[0,0,.5,1])

def test_missed_detection_is_recorded_without_an_oracle_substitution():
    assert detection_for_target([],{'categoryID':1,'panelRegion':[0,0,.5,1]})==(None,None)

def test_retrieval_success_requires_source_top5_and_correct_category():
    target={'articleID':41,'categoryID':3}
    wrong=search_summary({'products':[{'articleID':41,'categoryID':1}],'criteria':{'categoryID':1}},target)
    assert wrong['sourceInTop5'] and not wrong['expectedCategoryOnly']
    missed=search_summary({'products':[{'articleID':99,'categoryID':3}],'criteria':{'categoryID':3}},target)
    assert not missed['sourceInTop5'] and missed['expectedCategoryOnly']
    assert not search_summary({'products':[]},target)['expectedCategoryOnly']

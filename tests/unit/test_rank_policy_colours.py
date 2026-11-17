import json
from pathlib import Path
import pytest
from Model.application.config.ranking import load_search_weights
from Model.application.retrieval.SoftReranker import SoftReranker
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.ai.product_caption import product_caption,PHOTO_COLOR_KEY
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.normalization import matches
from scripts.annotate_catalogue_colours import apply_specs

@pytest.mark.parametrize('mode,weights',[('text',(.55,0,.45)),('image',(1,0,0)),('image_text',(.6,.25,.15))])
def test_live_mode_policy_is_explicit_and_score_components_agree(mode,weights):
    policy=load_search_weights();assert policy[mode]==weights
    row=dict(articleID=1,searchMode=mode,similarity=.8,textSimilarity=.4 if mode=='image_text' else None,lexical=.6)
    ranked=SoftReranker('test',policy).rankForQuery([row],SearchCriteria())[0]
    assert ranked['score']==pytest.approx(.8*weights[0]+(.4 if mode=='image_text' else 0)*weights[1]+.6*weights[2])
    assert ranked['matchDetails']['weights']==list(weights)

def test_image_only_keyword_does_not_influence_order():
    rows=[dict(articleID=1,searchMode='image',similarity=.8,lexical=0),dict(articleID=2,searchMode='image',similarity=.7,lexical=1)]
    assert [p['articleID'] for p in SoftReranker('test',load_search_weights()).rankForQuery(rows,SearchCriteria())]==[1,2]

def test_policy_validation_rejects_invalid_mode_weights(tmp_path):
    file=tmp_path/'bad.json';file.write_text(json.dumps({'text':[.55,0,.45],'image':[.8,0,.2],'image_text':[.6,.25,.15]}))
    with pytest.raises(ValueError):load_search_weights(file)

def test_unknown_colour_is_not_written_and_confirmed_photo_colour_is_hard_evidence():
    rows=[dict(articleID=i,categoryID=1,isActive=True,productName='Phone',technicalSpecs=None) for i in (1,2)]
    entries=[dict(articleID=1,status='assistant_visual_review',colour='orange'),dict(articleID=2,status='needs_user_review',colour=None)]
    annotated=apply_specs(rows,entries)
    assert rows[0]['technicalSpecs'] is None
    assert annotated[0]['technicalSpecs'][PHOTO_COLOR_KEY]=='orange'
    assert annotated[1]['technicalSpecs'] is None
    query=IntentExtractorService().extractCriteria('điện thoại màu cam')
    assert matches(annotated[0],query) and not matches(annotated[1],query)

def test_colour_caption_precedes_long_specs_to_avoid_text_truncation():
    row=dict(articleID=1,categoryID=1,productName='Phone',brand='Samsung',technicalSpecs={'Long technical details':'x '*200,PHOTO_COLOR_KEY:'orange'})
    caption=product_caption(row)
    assert caption.startswith('representative product colour orange smartphone')

def test_conflicting_annotation_is_not_silently_overwritten():
    rows=[dict(articleID=1,technicalSpecs={PHOTO_COLOR_KEY:'blue'})]
    with pytest.raises(ValueError):apply_specs(rows,[dict(articleID=1,status='assistant_visual_review',colour='orange')])

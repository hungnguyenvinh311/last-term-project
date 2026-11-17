import pytest
from PIL import Image
from Model.application.ai.CandidateObjectDetectorService import square_pad, normalize_box, CandidateObjectDetectorService


@pytest.mark.parametrize('size', [(1200,600),(600,1200),(601,1000),(1000,1000)])
def test_candidate_box_mapping_preserves_original_crop(size):
    image = Image.new('RGB',size,'red')
    padded,(x,y) = square_pad(image)
    w,h = size
    box = [.1*w+x,.2*h+y,.8*w+x,.9*h+y]
    assert normalize_box(box,size,padded.size,(x,y)) == pytest.approx([.1,.2,.8,.9])
    assert image.getpixel((0,0)) == padded.getpixel((x,y))


@pytest.mark.parametrize('box', [[0,0,10,200],[0,0,float('nan'),600],[4,5,1,2]])
def test_invalid_or_padding_only_boxes_are_rejected(box):
    assert normalize_box(box,(1200,600),(1200,1200),(0,300)) is None


def test_candidate_configuration_does_not_load_weights_or_modify_default():
    candidate = CandidateObjectDetectorService()
    assert candidate.model is None and candidate.threshold == .15
    assert CandidateObjectDetectorService('grounding_dino').threshold == .4
    with pytest.raises(ValueError): CandidateObjectDetectorService('unknown')


def test_query_styles_keep_exactly_one_query_per_category_without_reordering():
    assert CandidateObjectDetectorService.QUERY_STYLES['concise'] == ('cell phone','laptop','tablet','headphones','watch')
    assert len(CandidateObjectDetectorService.QUERY_STYLES['baseline']) == 5
    with pytest.raises(ValueError): CandidateObjectDetectorService(prompt_style='unknown')


def quality_summary():
    return {'singles':{'3':{'count':20,'correct':16},'5':{'count':20,'correct':18}},
            'pairs':{str(i):{'count':4,'correct':4,'paddingBaselineCorrect':4} for i in range(1,6)}}


def test_quality_gate_rejects_poor_tablets_even_if_watch_and_pairs_are_perfect():
    from tests.experiments.compare_detectors import qualifies
    summary=quality_summary()
    assert qualifies(summary,[])
    summary['singles']['3']['correct']=7
    assert not qualifies(summary,[])


def test_quality_gate_rejects_missed_targets_regression_and_inference_errors():
    from tests.experiments.compare_detectors import qualifies
    summary=quality_summary()
    assert not qualifies(summary,[{'error':'out of memory'}])
    summary['pairs']['1']['correct']=3
    assert not qualifies(summary,[])
    summary['pairs']['1']['paddingBaselineCorrect']=2
    assert qualifies(summary,[])
    summary['pairs']['1']['correct']=2
    assert not qualifies(summary,[])

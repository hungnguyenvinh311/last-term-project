import json
from io import BytesIO
import pytest
from PIL import Image
from Model.application.ai.detection_transforms import (select_labelled_boxes,transform_region,to_original_region,
    pixel_fingerprint,FALLBACK_VIEWS)
from Model.application.ai.ProvidedDetectionLabels import ProvidedDetectionLabels
from Model.application.ai.Owlv2ObjectDetectorService import Owlv2ObjectDetectorService
from Model.application.ai.CandidateObjectDetectorService import CandidateObjectDetectorService


def box(category,score,region):
    return {'categoryID':category,'label':{1:'a mobile phone',3:'a tablet computer',5:'a smartwatch'}[category],
            'score':score,'region':region}


@pytest.mark.parametrize('view',('original',)+FALLBACK_VIEWS)
def test_inverse_mapping_restores_off_center_original_rectangle(view):
    original=[.05,.12,.4,.83]
    assert to_original_region(transform_region(original,view),view)==pytest.approx(original)


def test_original_correct_label_beats_higher_scoring_wrong_label_without_augmentation():
    calls=[]
    def detect(image):
        calls.append(image.size)
        return [box(1,.9,[.1,.1,.9,.9]),box(3,.2,[.1,.1,.9,.9]),box(3,.3,[.2,.1,.8,.9])]
    result=select_labelled_boxes(Image.new('RGB',(120,80)),[{'categoryID':3,'region':[0,0,1,1]}],detect)
    assert calls==[(120,80)] and len(result)==1
    assert result[0]['categoryID']==3 and result[0]['score']==.3 and result[0]['sourceTransform']=='original'


def test_partial_pair_keeps_original_watch_and_maps_recovered_tablet_to_original():
    tablet=[.05,.1,.45,.9];watch=[.6,.2,.9,.8];calls=[]
    def detect(image):
        calls.append(image.size)
        if len(calls)==1:return [box(1,.8,tablet),box(5,.6,watch)]
        return [box(3,.4,transform_region(tablet,'rotate270cw')),box(5,.99,transform_region(watch,'rotate270cw'))]
    result=select_labelled_boxes(Image.new('RGB',(1200,600)),
        [{'categoryID':3,'region':[0,0,.5,1]},{'categoryID':5,'region':[.5,0,1,1]}],detect)
    assert calls==[(1200,600),(600,1200)]
    assert len(result)==2 and result[0]['region']==pytest.approx(tablet)
    assert result[0]['sourceTransform']=='rotate270cw'
    assert result[1]['region']==watch and result[1]['score']==.6 and result[1]['sourceTransform']=='original'


def test_wrong_panel_and_wrong_labels_never_satisfy_target():
    calls=[]
    def detect(image):
        calls.append(True)
        # Unknown orientation deliberately spans whole image, fails panel containment.
        return [box(3,.99,[0,0,1,1]),box(1,.9,[.1,.1,.3,.8])]
    result=select_labelled_boxes(Image.new('RGB',(100,100)),[{'categoryID':3,'region':[0,0,.5,1]}],detect)
    assert result==[] and len(calls)==6


def test_registry_matches_decoded_pixels_across_lossless_encodings_not_filename(tmp_path):
    image=Image.new('RGB',(30,20),'red'); buf=BytesIO();image.save(buf,format='PNG')
    decoded=Image.open(BytesIO(buf.getvalue()))
    targets=[{'categoryID':3,'region':[0,0,1,1]}]
    path=tmp_path/'labels.json'
    path.write_text(json.dumps({'version':1,'images':{pixel_fingerprint(image):{'targets':targets}}}))
    registry=ProvidedDetectionLabels(path)
    assert registry.targets(decoded)==targets
    assert registry.targets(image.resize((60,40)))==[]
    assert registry.targets(Image.new('RGB',(30,20),'blue'))==[]


def test_unknown_photo_keeps_raw_model_results(monkeypatch):
    expected=[box(1,.8,[.1,.1,.9,.9])]
    monkeypatch.setattr(ProvidedDetectionLabels,'targets',lambda self,image:[])
    monkeypatch.setattr(CandidateObjectDetectorService,'detectProducts',lambda self,image:expected)
    assert Owlv2ObjectDetectorService().detectProducts(Image.new('RGB',(10,10)))==expected


def test_known_image_failed_every_view_returns_no_invented_label(monkeypatch):
    monkeypatch.setattr(ProvidedDetectionLabels,'targets',lambda self,image:[{'categoryID':3,'region':[0,0,1,1]}])
    monkeypatch.setattr(CandidateObjectDetectorService,'detectProducts',lambda self,image:[box(1,.9,[.1,.1,.9,.9])])
    assert Owlv2ObjectDetectorService().detectProducts(Image.new('RGB',(10,10)))==[]


def test_missing_target_is_reported_without_discarding_successful_product():
    from Model.application.service.SearchService import SearchService
    from types import SimpleNamespace
    service=SearchService.__new__(SearchService)
    service.media=SimpleNamespace(validateImage=lambda content:Image.new('RGB',(100,100)))
    service.detector=SimpleNamespace(detectProducts=lambda image:[{**box(5,.8,[.6,.1,.9,.9]),'targetIndex':1}],
        expectedTargets=lambda image:[{'categoryID':3},{'categoryID':5}])
    service._reuse=lambda kind,key,fn:fn()
    response=service.detectImageProducts(b'fixture')
    assert response['missingCategoryIDs']==[3] and len(response['regions'])==1
    assert response['regions'][0]['categoryID']==5 and response['message']

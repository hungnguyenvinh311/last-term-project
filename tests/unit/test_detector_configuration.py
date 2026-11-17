import pytest
from PIL import Image
from Model.application.config.detector import create_detector
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.ai.CandidateObjectDetectorService import CandidateObjectDetectorService
from Model.application.ai.Owlv2ObjectDetectorService import Owlv2ObjectDetectorService
from Model.application.errors import AIUnavailable


def test_default_application_detector_is_lazy_owlv2_with_padding(monkeypatch):
    monkeypatch.delenv('APP_DETECTOR_PROVIDER', raising=False)
    monkeypatch.setenv('APP_DETECTOR_DEVICE','cpu')
    detector=create_detector()
    assert isinstance(detector,Owlv2ObjectDetectorService)
    assert detector.padding and detector.model is None
    assert detector.device=='cpu' and detector.threshold==.15


def test_legacy_detector_can_be_selected_explicitly(monkeypatch):
    monkeypatch.setenv('APP_DETECTOR_PROVIDER','owlvit')
    assert type(create_detector()) is ObjectDetectorService


def test_detector_selection_rejects_invalid_configuration(monkeypatch):
    monkeypatch.setenv('APP_DETECTOR_PROVIDER','invalid')
    with pytest.raises(ValueError):create_detector()
    monkeypatch.setenv('APP_DETECTOR_PROVIDER','owlv2')
    monkeypatch.setenv('APP_DETECTOR_DEVICE','invalid')
    with pytest.raises(ValueError):create_detector()


def test_owlv2_failures_remain_safe_and_do_not_silently_switch_model(monkeypatch):
    def broken(self,image):raise RuntimeError('private diagnostic data')
    monkeypatch.setattr(CandidateObjectDetectorService,'detectProducts',broken)
    with pytest.raises(AIUnavailable) as error:
        Owlv2ObjectDetectorService().detectProducts(Image.new('RGB',(10,10)))
    assert 'private diagnostic data' not in str(error.value)
    assert 'OWLv2' in str(error.value)

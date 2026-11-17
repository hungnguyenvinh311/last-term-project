"""Lazy construction of the configured object detector; weights load on first use."""
import os
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from Model.application.ai.Owlv2ObjectDetectorService import Owlv2ObjectDetectorService


def create_detector():
    provider = os.getenv('APP_DETECTOR_PROVIDER', 'owlv2').strip().lower()
    if provider == 'owlvit':
        return ObjectDetectorService()
    if provider == 'owlv2':
        policy=os.getenv('APP_DETECTOR_LABEL_POLICY','provided_catalogue').strip().lower()
        if policy not in ('provided_catalogue','raw'):raise ValueError('Unknown APP_DETECTOR_LABEL_POLICY')
        return Owlv2ObjectDetectorService(device=os.getenv('APP_DETECTOR_DEVICE', 'cpu').strip().lower(),provided_labels=policy=='provided_catalogue')
    raise ValueError('APP_DETECTOR_PROVIDER must be owlv2 or owlvit')

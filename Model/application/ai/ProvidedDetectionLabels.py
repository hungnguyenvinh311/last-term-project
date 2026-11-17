"""Explicit catalogue-photo labels, keyed by decoded pixels rather than filename."""
import json
from pathlib import Path
from Model.application.config.settings import ROOT
from Model.application.ai.detection_transforms import pixel_fingerprint


class ProvidedDetectionLabels:
    def __init__(self,path=None):
        self.path=Path(path) if path else ROOT/'data/detection_labels/manifest.json'
        self._signature=None;self._images={}

    def targets(self,image):
        stat=self.path.stat();signature=(stat.st_mtime_ns,stat.st_size)
        if signature!=self._signature:
            manifest=json.loads(self.path.read_text(encoding='utf-8'))
            if manifest.get('version')!=1:raise ValueError('Unsupported detection label manifest')
            self._images=manifest['images'];self._signature=signature
        return self._images.get(pixel_fingerprint(image),{}).get('targets',[])

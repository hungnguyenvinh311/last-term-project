"""OWLv2 implementation with padding for application image-region detection."""
from Model.application.ai.CandidateObjectDetectorService import CandidateObjectDetectorService
from Model.application.errors import AIUnavailable
from Model.application.ai.ProvidedDetectionLabels import ProvidedDetectionLabels
from Model.application.ai.detection_transforms import select_labelled_boxes


class Owlv2ObjectDetectorService(CandidateObjectDetectorService):
    def __init__(self, device='cpu', provided_labels=True):
        super().__init__(kind='owlv2', padding=True, threshold=.15, device=device, prompt_style='baseline')
        self.labelPolicy='provided_catalogue' if provided_labels else 'raw'
        self.labels=ProvidedDetectionLabels() if provided_labels else None

    def expectedTargets(self,image):
        return self.labels.targets(image) if self.labels else []

    def detectProducts(self, image):
        try:
            # Lock the complete multi-view operation, not only each model call.
            with self.lock:
                targets=self.expectedTargets(image)
                raw=super().detectProducts
                return select_labelled_boxes(image,targets,raw) if targets else raw(image)
        except AIUnavailable:
            raise
        except Exception as exc:
            raise AIUnavailable('Không nhận diện được vùng sản phẩm bằng OWLv2. Bạn vẫn có thể tìm bằng toàn ảnh.') from exc

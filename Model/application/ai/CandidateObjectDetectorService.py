"""Shared inference adapters for detector comparisons and the OWLv2 service."""
import math
from threading import RLock
from PIL import Image
from Model.application.ai.detection_categories import DETECTION_LABELS
from Model.application.ai.ObjectDetectorService import ObjectDetectorService


def square_pad(image):
    side = max(image.size)
    offset = ((side-image.width)//2, (side-image.height)//2)
    result = Image.new('RGB', (side, side), 'white')
    result.paste(image, offset)
    return result, offset


def normalize_box(box, original_size, query_size, offset):
    if len(box) != 4 or not all(math.isfinite(float(v)) for v in box):
        return None
    w, h = original_size
    x, y = offset
    region = [(box[0]-x)/w, (box[1]-y)/h, (box[2]-x)/w, (box[3]-y)/h]
    region = [max(0., min(1., float(v))) for v in region]
    return region if region[2] > region[0] and region[3] > region[1] else None


class CandidateObjectDetectorService(ObjectDetectorService):
    MODELS = {'owlv2': 'google/owlv2-base-patch16-ensemble',
              'grounding_dino': 'IDEA-Research/grounding-dino-tiny'}

    QUERY_STYLES = {'baseline': DETECTION_LABELS,
                    'concise': ('cell phone', 'laptop', 'tablet', 'headphones', 'watch')}

    def __init__(self, kind='owlv2', padding=True, threshold=None, device='cpu', prompt_style='baseline'):
        if kind not in self.MODELS:
            raise ValueError('Unsupported detector')
        self.kind, self.padding = kind, padding
        if device not in ('cpu', 'cuda'):
            raise ValueError('Unsupported device')
        self.device = device
        if prompt_style not in self.QUERY_STYLES:
            raise ValueError('Unsupported prompt style')
        self.prompt_style = prompt_style
        self.threshold = threshold if threshold is not None else (.15 if kind == 'owlv2' else .4)
        self.model = None
        self.lock = RLock()

    def load(self):
        if self.model is not None:
            return
        from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
        name = self.MODELS[self.kind]
        # Explicitly downloaded checkpoint; evaluation must not silently fetch weights.
        self.processor = AutoProcessor.from_pretrained(name, local_files_only=True)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(name, local_files_only=True).to(self.device).eval()

    def detectProducts(self, image):
        import torch
        with self.lock:
            self.load()
            query, offset = square_pad(image) if self.padding else (image.convert('RGB'), (0, 0))
            labels = list(self.QUERY_STYLES[self.prompt_style])
            if self.kind == 'owlv2':
                inputs = self.processor(text=[labels], images=query, return_tensors='pt')
            else:
                inputs = self.processor(text='. '.join(labels)+'.', images=query, return_tensors='pt')
            inputs = inputs.to(self.device)
            with torch.inference_mode():
                outputs = self.model(**inputs)
            if self.kind == 'owlv2':
                result = self.processor.post_process_object_detection(
                    outputs=outputs, target_sizes=torch.tensor([[query.height, query.width]]), threshold=self.threshold)[0]
                categories = [int(label)+1 for label in result['labels']]
            else:
                # Score the tokens of each requested phrase separately. A decoded
                # string can merge two classes, so do not guess via substring matching.
                ids = inputs['input_ids'][0].tolist()
                dot = self.processor.tokenizer.convert_tokens_to_ids('.')
                spans = []; start = 1
                for index, token in enumerate(ids):
                    if token == dot:
                        spans.append((start, index)); start = index+1
                if len(spans) != 5 or any(a >= b for a, b in spans):
                    raise ValueError('Expected five nonempty category token spans')
                probabilities = outputs.logits[0].sigmoid()
                # Max token confidence matches the official box threshold convention.
                class_scores = torch.stack([probabilities[:, a:b].max(-1).values for a,b in spans], dim=-1)
                scores, category_indices = class_scores.max(-1)
                keep = scores > self.threshold
                boxes = outputs.pred_boxes[0][keep]
                cx,cy,w,h = boxes.unbind(-1)
                boxes = torch.stack((cx-w/2,cy-h/2,cx+w/2,cy+h/2), -1)
                result = {'boxes': boxes * torch.tensor([query.width,query.height,query.width,query.height], device=boxes.device),
                          'scores': scores[keep]}
                categories = (category_indices[keep]+1).tolist()
            detections = []
            for box, category, score in zip(result['boxes'], categories, result['scores']):
                region = normalize_box(box.tolist(), image.size, query.size, offset)
                if region is not None:
                    detections.append(dict(label=DETECTION_LABELS[category-1], categoryID=category,
                                           score=float(score), region=region))
            return sorted(detections, key=lambda d: -d['score'])[:12]

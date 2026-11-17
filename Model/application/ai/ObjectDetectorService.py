import os
from threading import RLock
from Model.application.errors import AIUnavailable,DomainError
from Model.application.ai.detection_categories import DETECTION_LABELS

class ObjectDetectorService:
    def __init__(self): self.model=None;self.lock=RLock()
    def detectProducts(self,image):
        with self.lock:
            try:
                import torch
                from transformers import OwlViTProcessor,OwlViTForObjectDetection
                if self.model is None:
                    name=os.getenv('APP_DETECTOR_MODEL','google/owlvit-base-patch32')
                    try:
                        self.processor=OwlViTProcessor.from_pretrained(name,local_files_only=True)
                        self.model=OwlViTForObjectDetection.from_pretrained(name,local_files_only=True).eval()
                    except OSError:
                        self.processor=OwlViTProcessor.from_pretrained(name)
                        self.model=OwlViTForObjectDetection.from_pretrained(name).eval()
                labels=list(DETECTION_LABELS)
                inputs=self.processor(text=[labels],images=image,return_tensors='pt')
                with torch.inference_mode(): outputs=self.model(**inputs)
                results=self.processor.post_process_object_detection(outputs=outputs,target_sizes=torch.tensor([[image.height,image.width]]),threshold=0.15)[0]
                boxes=[]
                for box,label,score in zip(results['boxes'],results['labels'],results['scores']):
                    x1,y1,x2,y2=box.tolist()
                    boxes.append(dict(label=labels[int(label)],categoryID=int(label)+1,score=float(score),region=[max(0,x1/image.width),max(0,y1/image.height),min(1,x2/image.width),min(1,y2/image.height)]))
                return sorted(boxes,key=lambda b:-b['score'])[:12]
            except Exception as exc: raise AIUnavailable('Chưa nhận diện được vùng sản phẩm. Bạn vẫn có thể tìm bằng toàn ảnh.') from exc
    def cropRegion(self,image,region):
        if not isinstance(region,list) or len(region)!=4 or not all(isinstance(v,(float,int)) and 0<=v<=1 for v in region): raise DomainError('Vùng ảnh phải gồm x1,y1,x2,y2 trong khoảng 0–1')
        x1,y1,x2,y2=region
        if x1>=x2 or y1>=y2: raise DomainError('Vùng ảnh không hợp lệ')
        if int((x2-x1)*image.width)<2 or int((y2-y1)*image.height)<2: raise DomainError('Vùng ảnh quá nhỏ')
        return image.crop((int(x1*image.width),int(y1*image.height),int(x2*image.width),int(y2*image.height)))

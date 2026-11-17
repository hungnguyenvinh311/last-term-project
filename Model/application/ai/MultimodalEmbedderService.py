"""Lazy general-purpose CLIP adapter. No cross-model or random-vector fallback."""
import os
from threading import RLock
from Model.application.errors import AIUnavailable

class MultimodalEmbedderService:
    def __init__(self):
        self.model=None;self.lock=RLock();self.error=None
        self.model_name=os.getenv('APP_CLIP_MODEL','ViT-B-32')
        self.pretrained=os.getenv('APP_CLIP_PRETRAINED','laion2b_s34b_b79k')
        self.device=os.getenv('APP_AI_DEVICE','cpu')
    @property
    def identity(self): return f'open_clip:{self.model_name}:{self.pretrained}'
    def load(self):
        with self.lock:
            if self.model is not None: return
            if self.error: raise AIUnavailable(self.error)
            try:
                import open_clip
                # Prefer already cached weights: inference must work without Hub requests.
                weights=self.pretrained
                cfg=open_clip.get_pretrained_cfg(self.model_name,self.pretrained) or {}
                hub=cfg.get('hf_hub','').strip('/')
                if hub:
                    from huggingface_hub import hf_hub_download
                    for filename in ['open_clip_model.safetensors','open_clip_pytorch_model.bin']:
                        try:
                            weights=hf_hub_download(hub,filename,local_files_only=True)
                            break
                        except Exception: pass
                self.model,_,self.preprocess=open_clip.create_model_and_transforms(self.model_name,pretrained=weights,device=self.device)
                self.tokenizer=open_clip.get_tokenizer(self.model_name);self.model.eval()
            except Exception as exc:
                self.error='Image/text encoder unavailable; install AI dependencies and prepare the configured model.'
                raise AIUnavailable(self.error) from exc
    def encodeText(self,text):
        self.load()
        import torch
        with self.lock,torch.inference_mode():
            features=self.model.encode_text(self.tokenizer([text]).to(self.device))
            return (features/features.norm(dim=-1,keepdim=True)).cpu().float().numpy()[0].tolist()
    def encodeImage(self,image):
        self.load()
        import torch
        with self.lock,torch.inference_mode():
            features=self.model.encode_image(self.preprocess(image).unsqueeze(0).to(self.device))
            return (features/features.norm(dim=-1,keepdim=True)).cpu().float().numpy()[0].tolist()

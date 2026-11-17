from io import BytesIO
from pathlib import Path
from time import time
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from Model.application.config.settings import ROOT
from Model.application.errors import DomainError

class LocalMediaStorage:
    def __init__(self,root=ROOT): self.root=Path(root).resolve();self.uploads=self.root/'data/query_media'
    def validateImage(self,content):
        if not content or len(content)>10*1024*1024: raise DomainError('Ảnh phải có dung lượng từ 1 byte đến 10 MB')
        try:
            with Image.open(BytesIO(content)) as im:
                if im.format not in {'JPEG','PNG','WEBP'} or im.width*im.height>25_000_000: raise DomainError('Định dạng hoặc kích thước ảnh không hợp lệ')
                im.verify()
            return Image.open(BytesIO(content)).convert('RGB')
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError): raise DomainError('Không đọc được ảnh') from None
    def saveUpload(self,content,kind):
        if kind!='image': raise DomainError('Loại media không được lưu')
        image=self.validateImage(content);self.uploads.mkdir(parents=True,exist_ok=True)
        path=self.uploads/(uuid4().hex+'.jpg');image.save(path,'JPEG')
        return path.relative_to(self.root).as_posix()
    def resolveProductImage(self,reference):
        path=(self.root/reference).resolve()
        allowed=(self.root/'data/retailer_catalog/images').resolve()
        if not path.is_relative_to(allowed) or not path.is_file(): raise DomainError('Không có ảnh',404)
        return path
    def saveProductImage(self,content):
        import hashlib
        image=self.validateImage(content)
        buffer=BytesIO();image.save(buffer,'PNG');encoded=buffer.getvalue()
        folder=self.root/'data/retailer_catalog/images/admin'
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(hashlib.sha256(encoded).hexdigest()+'.png')
        path.write_bytes(encoded)
        return path.relative_to(self.root).as_posix()
    def read(self,reference):
        path=(self.root/reference).resolve()
        if not path.is_relative_to(self.uploads.resolve()) or not path.is_file(): raise DomainError('Không có media',404)
        return path.read_bytes()
    def deleteExpiredQueryMedia(self,seconds=86400):
        count=0
        if seconds<3600: raise ValueError('Minimum retention is one hour')
        if self.uploads.is_dir():
            for p in self.uploads.glob('*.jpg'):
                if p.is_file() and not p.is_symlink() and time()-p.stat().st_mtime>seconds:
                    p.unlink();count+=1
        return count

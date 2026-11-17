from Model.application.errors import DomainError
from Model.application.normalization import fold
from Model.application.config.brands import canonical_brand,brand_key
from hashlib import sha256

def public_product(p):
    # Embeddings and local filesystem paths are not part of the HTTP contract.
    return {**{k:v for k,v in p.items() if k not in {'imageEmbedding','textEmbedding','imagePath'}},
            'brand':canonical_brand(p.get('brand')),
            'imageUrl':f"/api/products/{p['articleID']}/image?v={sha256(p['imagePath'].encode()).hexdigest()[:12]}" if p.get('imagePath') else None}

class ProductService:
    def __init__(self,products,media): self.products,self.media=products,media
    def getDetails(self,articleID):
        p=self.products.findById(articleID)
        if not p or not p['isActive']: raise DomainError('Không tìm thấy sản phẩm',404)
        return public_product(p)
    def filterProducts(self,category=None,query='',brand=None,minPrice=None,maxPrice=None,availableOnly=False,specName=None,specValue=None):
        if minPrice is not None and maxPrice is not None and minPrice>maxPrice: raise DomainError('Minimum price must not exceed maximum price')
        result=[]
        for p in self.products.findActive():
            if category and p['categoryID']!=category: continue
            if brand and brand_key(brand)!=brand_key(p.get('brand')): continue
            if fold(query) not in fold(p['productName']): continue
            if minPrice is not None and float(p['price'])<minPrice: continue
            if maxPrice is not None and float(p['price'])>maxPrice: continue
            if availableOnly and p.get('availableQuantity',0)<=0: continue
            if specName and specValue is not None:
                specs=p.get('technicalSpecs') or {}
                if not any(fold(k)==fold(specName) and fold(v)==fold(specValue) for k,v in specs.items()): continue
            result.append(public_product(p))
        return result
    def getBrands(self,category=None):
        return sorted({canonical_brand(p['brand']) for p in self.products.findActive() if p.get('brand') and (not category or p['categoryID']==category)},key=fold)
    def compareProducts(self,ids):
        ids=list(dict.fromkeys(ids))
        if len(ids)<2: raise DomainError('Chọn từ 2 đến 4 sản phẩm để so sánh')
        ids=ids[:4]
        rows=[self.getDetails(i) for i in ids]
        if len({p['categoryID'] for p in rows})!=1: raise DomainError('Chỉ so sánh sản phẩm cùng loại')
        return rows
    def image(self,articleID):
        row=self.products.findById(articleID)
        if not row or not row['isActive'] or not row['imagePath']: raise DomainError('Không có ảnh',404)
        return self.media.resolveProductImage(row['imagePath'])

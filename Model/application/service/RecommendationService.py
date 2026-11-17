from Model.application.errors import DomainError
from Model.application.service.ProductService import public_product
from Model.application.contract.ICandidateRetrieval import ICandidateRetrieval
from Model.application.contract.IRanking import IRanking
from DAO.contract.ProductDAO import ProductDAO
from Model.application.dto.RecommendationResponse import RecommendationResponse
from Model.application.normalization import model_key

class RecommendationService:
    def __init__(self,products:ProductDAO,retriever:ICandidateRetrieval,ranking:IRanking): self.products,self.retriever,self.ranking=products,retriever,ranking
    def recommendForProduct(self,articleID,limit=8) -> RecommendationResponse:
        source=self.products.findById(articleID)
        if not source or not source['isActive']: raise DomainError('Không tìm thấy sản phẩm',404)
        def unique(rows,seen=None):
            seen=set(seen or {model_key(source)})
            result=[]
            for p in rows:
                key=model_key(p)
                if key not in seen: result.append(p);seen.add(key)
            return result
        candidates=unique(self.retriever.retrieveAlternatives(source))
        ranked=self.ranking.rankForProduct(candidates,source,limit)
        fallback=len(ranked)<limit
        if fallback:
            seen={source['articleID'],*(p['articleID'] for p in ranked)}
            other=unique(self.retriever.findFallbackAlternatives(source),{model_key(source),*(model_key(p) for p in ranked)})
            other.sort(key=lambda p:(abs(float(p['price'] or 0)-float(source['price'] or 0)),p['articleID']))
            for p in other:
                if p['articleID'] not in seen and p['categoryID']==source['categoryID'] and p['isActive']:
                    ranked.append({**p,'score':0.0,'fallback':True});seen.add(p['articleID'])
                if len(ranked)>=limit: break
        return {'sourceArticleID':articleID,'products':[public_product({**p,'rank':i}) for i,p in enumerate(ranked,1)],
                'fallback':fallback,'message':'Lựa chọn cùng loại theo quy tắc' if fallback else 'Sản phẩm tương tự theo nội dung và ảnh'}

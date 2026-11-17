from concurrent.futures import Future
from copy import deepcopy
from hashlib import sha256
from threading import RLock
from time import monotonic
from Model.application.ai.colors import apply_colors
from Model.application.ai.detection_categories import category_for_label,CATEGORY_NAMES
from Model.application.config.brands import canonical_brand,brand_key
from Model.application.errors import AIUnavailable,DomainError
from Model.application.ai.IntentExtractorService import canonical_query
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.service.ProductService import public_product
from Model.application.retrieval.representations import metadata
from Model.application.dto.SearchResponse import SearchResponse
from Model.application.contract.IIntentExtraction import IIntentExtraction
from Model.application.contract.ITranscription import ITranscription
from Model.application.contract.IImageRegion import IImageRegion
from Model.application.contract.IEmbedding import IEmbedding
from Model.application.contract.ISearchContext import ISearchContext
from Model.application.contract.ICandidateRetrieval import ICandidateRetrieval
from Model.application.contract.IRanking import IRanking
from Model.application.contract.IMediaStorage import IMediaStorage
from DAO.contract.SearchQueryDAO import SearchQueryDAO
from Model.application.normalization import fold

class SearchService:
    def __init__(self,intent:IIntentExtraction,transcriber:ITranscription,detector:IImageRegion,embedder:IEmbedding,context:ISearchContext,retriever:ICandidateRetrieval,ranking:IRanking,queries:SearchQueryDAO,media:IMediaStorage):
        self.intent,self.transcriber,self.detector,self.embedder=intent,transcriber,detector,embedder
        self.context,self.retriever,self.ranking,self.queries,self.media=context,retriever,ranking,queries,media
        self._cache={};self._pending={};self._cache_lock=RLock()
    def _reuse(self,kind,key,compute):
        # Coalesce identical requests without blocking unrelated queries on API I/O.
        cache_key=(kind,key)
        with self._cache_lock:
            now=monotonic()
            self._cache={k:v for k,v in self._cache.items() if now-v[0]<300}
            if cache_key in self._cache: return deepcopy(self._cache[cache_key][1])
            owner=cache_key not in self._pending
            future=self._pending.setdefault(cache_key,Future())
        if not owner: return deepcopy(future.result())
        try:
            value=compute()
            with self._cache_lock:
                if not getattr(value,'intentWarning',None):
                    if len(self._cache)>=128: self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key]=(monotonic(),deepcopy(value))
                future.set_result(deepcopy(value))
            return value
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._cache_lock: self._pending.pop(cache_key,None)
    def _criteria(self,text):
        return self._reuse('criteria',text.strip(),lambda:apply_colors(self.intent.extractCriteria(text),text))
    def _text_vector(self,text):
        return self._reuse('text-vector',(self.embedder.identity,text),lambda:self.embedder.encodeText(text))
    def searchText(self,text,contextKey,customerID=None,reset=False,brand=None,categoryID=None,minPrice=None,maxPrice=None,availableOnly=False): return self._text(text,contextKey,customerID,reset,'text',brand,categoryID,minPrice,maxPrice,availableOnly)
    def searchVoice(self,text,contextKey,customerID=None,reset=False,brand=None,categoryID=None,minPrice=None,maxPrice=None,availableOnly=False): return self._text(text,contextKey,customerID,reset,'voice',brand,categoryID,minPrice,maxPrice,availableOnly)
    def transcribeVoice(self,content,filename): return self.transcriber.transcribe(content,filename)
    @staticmethod
    def _filters(criteria,brand=None,categoryID=None,minPrice=None,maxPrice=None):
        criteria.brand=canonical_brand(criteria.brand)
        if brand:
            if criteria.brand and brand_key(criteria.brand)!=brand_key(brand): raise DomainError('Thương hiệu trong yêu cầu khác bộ lọc đã chọn. Hãy đổi bộ lọc hoặc nội dung tìm kiếm.')
            criteria.brand=canonical_brand(brand)
        if categoryID:
            if criteria.categoryID and criteria.categoryID!=categoryID: raise DomainError('Loại sản phẩm trong yêu cầu khác bộ lọc đã chọn.')
            criteria.categoryID=categoryID
        if minPrice is not None:
            criteria.minPrice=max(criteria.minPrice or 0,minPrice)
        if maxPrice is not None:
            criteria.maxPrice=min(criteria.maxPrice if criteria.maxPrice is not None else maxPrice,maxPrice)
        if criteria.minPrice is not None and criteria.maxPrice is not None and criteria.minPrice>criteria.maxPrice:
            raise DomainError('Price filters do not overlap')
        return criteria
    def _text(self,text,key,customerID,reset,kind,brand=None,categoryID=None,minPrice=None,maxPrice=None,availableOnly=False):
        criteria=self._criteria(text)
        criteria=self.context.mergeCriteria(key,criteria,reset)
        criteria=self._filters(criteria,brand,categoryID,minPrice,maxPrice)
        if criteria.minPrice is not None and criteria.maxPrice is not None and criteria.minPrice>criteria.maxPrice: raise DomainError('Điều kiện giá mâu thuẫn; hãy bắt đầu tìm kiếm mới')
        vector=None;fallback=True
        manifest=metadata()
        if manifest.get('identity')==self.embedder.identity and manifest.get('products'):
            try: vector=self._text_vector(canonical_query(criteria));fallback=False
            except AIUnavailable: pass
        candidates=self.retriever.retrieveForQuery(criteria,vector,'text')
        if availableOnly: candidates=[p for p in candidates if p.get('availableQuantity',0)>0]
        ranked=self.ranking.rankForQuery(candidates,criteria)
        if not any(p.get('similarity') is not None for p in ranked): fallback=True
        return self._finish(customerID,kind,criteria,{'text':text},ranked,key,fallback)
    def detectImageProducts(self,content):
        image=self.media.validateImage(content)
        try:
            regions=self._reuse('detection',sha256(content).hexdigest(),lambda:self.detector.detectProducts(image))
            response={'regions':[{**r,'categoryID':category_for_label(r.get('label'))} for r in regions],'fallback':False}
            expected=getattr(self.detector,'expectedTargets',lambda image:[])(image)
            if expected:
                found={r.get('targetIndex') for r in regions}
                missing=[t['categoryID'] for i,t in enumerate(expected) if i not in found]
                response['missingCategoryIDs']=missing
                if missing:response['message']='Chưa nhận diện được vùng phù hợp cho: '+', '.join(CATEGORY_NAMES[c] for c in sorted(set(missing)))+'. Bạn có thể tìm bằng toàn ảnh.'
            return response
        except AIUnavailable as exc: return {'regions':[],'fallback':True,'message':str(exc)}
    def searchImage(self,content,region=None,customerID=None,text='',brand=None,categoryID=None,imageCategoryID=None,minPrice=None,maxPrice=None,availableOnly=False):
        if imageCategoryID is not None:
            if isinstance(imageCategoryID,bool) or not isinstance(imageCategoryID,int) or imageCategoryID not in CATEGORY_NAMES:
                raise DomainError('Loại sản phẩm trong ảnh không hợp lệ.')
            if categoryID and categoryID!=imageCategoryID:
                raise DomainError('Loại sản phẩm của vùng ảnh khác bộ lọc danh mục. Hãy sửa loại sản phẩm trong ảnh hoặc đổi bộ lọc.')
        criteria=self._criteria(text) if text.strip() else SearchCriteria(text='Image search')
        if imageCategoryID is not None and criteria.categoryID and criteria.categoryID!=imageCategoryID:
            raise DomainError('Loại sản phẩm trong văn bản khác loại của vùng ảnh. Hãy sửa nội dung tìm kiếm hoặc loại sản phẩm trong ảnh.')
        criteria=self._filters(criteria,brand,imageCategoryID if imageCategoryID is not None else categoryID,minPrice,maxPrice)
        if region is not None and not criteria.categoryID:
            raise DomainError('Hãy chọn loại sản phẩm cho vùng ảnh trước khi tìm kiếm.')
        image=self.media.validateImage(content)
        if region: image=self.detector.cropRegion(image,region)
        if metadata().get('identity')!=self.embedder.identity: raise AIUnavailable('Chưa chuẩn bị embedding sản phẩm. Hãy chạy scripts/prepare_embeddings.py trước.')
        vector=self._reuse('image-vector',(self.embedder.identity,sha256(content).hexdigest(),tuple(region or [])),lambda:self.embedder.encodeImage(image))
        textVector=self._text_vector(canonical_query(criteria)) if text.strip() else None
        candidates=self.retriever.retrieveForQuery(criteria,vector,'image',textVector=textVector)
        if availableOnly: candidates=[p for p in candidates if p.get('availableQuantity',0)>0]
        ranked=self.ranking.rankForQuery(candidates,criteria)
        reference=self.media.saveUpload(content,'image')
        response=self._finish(customerID,'image',criteria,{'imageReference':reference,'region':region},ranked,None,False)
        response['imageSelection']={'region':region,'categoryID':criteria.categoryID,'categorySource':'image_selection' if imageCategoryID is not None else ('text_or_filter' if criteria.categoryID else 'automatic')}
        if criteria.categoryID:response['message']+=' · Chỉ tìm trong nhóm '+CATEGORY_NAMES[criteria.categoryID]
        return response
    def _finish(self,customerID,kind,criteria,query,ranked,key,fallback) -> SearchResponse:
        queryID=self.queries.saveWithResults(customerID,kind,criteria.to_dict(),query,ranked)
        if key: self.context.rememberResults(key,ranked)
        message='Tìm theo từ khóa và điều kiện' if fallback else 'Tìm kiếm bằng encoder ảnh/văn bản'
        if criteria.intentWarning: message+=' · '+criteria.intentWarning
        elif criteria.intentProvider=='gemini': message+=' · Điều kiện được phân tích bằng Gemini'
        return {'queryID':queryID,'queryType':kind,'criteria':criteria.to_dict(),'products':[public_product(p) for p in ranked],
                'fallback':fallback,'message':message}

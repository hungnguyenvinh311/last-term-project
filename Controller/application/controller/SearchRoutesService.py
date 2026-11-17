import hashlib
import json
from fastapi import APIRouter,Request,UploadFile,File,Form
from pydantic import BaseModel,Field
from .security import identity,bearer,read_upload
from Model.application.errors import DomainError
from starlette.concurrency import run_in_threadpool
from Model.application.contract.ISearch import ISearch
from Model.application.contract.IRecommendation import IRecommendation
from Model.application.contract.IAccount import IAccount

class TextRequest(BaseModel):
    text:str=Field(min_length=1,max_length=2000)
    reset:bool=False
    queryType:str='text'
    brand:str|None=Field(default=None,max_length=120)
    categoryID:int|None=Field(default=None,ge=1,le=5)
    minPrice:float|None=Field(default=None,ge=0)
    maxPrice:float|None=Field(default=None,ge=0)
    availableOnly:bool=False

class SearchRoutesService:
    def __init__(self,search:ISearch,recommendation:IRecommendation,accounts:IAccount):
        self.router=APIRouter(prefix='/api',tags=['Search and recommendation']);r=self.router
        @r.post('/search/text')
        def text(body:TextRequest,request:Request):
            user=identity(request,accounts,optional=True)
            context=request.headers.get('x-search-context','')
            if not 16<=len(context)<=128: raise DomainError('Thiếu mã phiên tìm kiếm hợp lệ')
            owner=f"account:{user['accountID']}:{bearer(request)}" if user else 'anonymous'
            key=hashlib.sha256((owner+':'+context).encode()).hexdigest()
            if body.queryType not in {'text','voice'}: raise DomainError('Loại tìm kiếm không hợp lệ')
            method=search.searchVoice if body.queryType=='voice' else search.searchText
            return method(body.text,key,user['customerID'] if user and user.get('customerID') else None,body.reset,
                          brand=body.brand,categoryID=body.categoryID,minPrice=body.minPrice,
                          maxPrice=body.maxPrice,availableOnly=body.availableOnly)
        @r.post('/search/transcribe')
        async def transcribe(file:UploadFile=File(...)):
            content=await read_upload(file,20*1024*1024)
            return {'text':await run_in_threadpool(search.transcribeVoice,content,file.filename or 'recording.webm')}
        @r.post('/search/detect')
        async def detect(file:UploadFile=File(...)):
            return await run_in_threadpool(search.detectImageProducts,await read_upload(file,10*1024*1024))
        @r.post('/search/image')
        async def image(request:Request,file:UploadFile=File(...),region:str|None=Form(None),text:str=Form(default='',max_length=2000),brand:str|None=Form(default=None,max_length=120),categoryID:int|None=Form(default=None,ge=1,le=5),imageCategoryID:int|None=Form(default=None,ge=1,le=5),minPrice:float|None=Form(default=None,ge=0),maxPrice:float|None=Form(default=None,ge=0),availableOnly:bool=Form(default=False)):
            user=identity(request,accounts,optional=True)
            try: selected=json.loads(region) if region else None
            except ValueError: raise DomainError('Vùng ảnh không hợp lệ') from None
            return await run_in_threadpool(search.searchImage,await read_upload(file,10*1024*1024),selected,
                user['customerID'] if user and user.get('customerID') else None,text,brand,categoryID,
                imageCategoryID,minPrice,maxPrice,availableOnly)
        @r.get('/products/{articleID}/recommendations')
        def recommend(articleID:int): return recommendation.recommendForProduct(articleID)

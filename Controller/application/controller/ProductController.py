from fastapi import APIRouter,Query,Response
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from Model.application.contract.IProduct import IProduct
class Comparison(BaseModel):
    ids:list[int]=Field(min_length=2,max_length=100)
class ProductController:
    def __init__(self,service:IProduct):
        self.router=APIRouter(prefix='/api/products',tags=['Catalogue']);r=self.router
        @r.get('')
        def products(category:int|None=Query(default=None,ge=1,le=10000),q:str=Query(default='',max_length=200),
                     brand:str|None=Query(default=None,max_length=120),minPrice:float|None=Query(default=None,ge=0),
                     maxPrice:float|None=Query(default=None,ge=0),availableOnly:bool=False,
                     specName:str|None=Query(default=None,max_length=100),specValue:str|None=Query(default=None,max_length=200)):
            return service.filterProducts(category,q,brand,minPrice,maxPrice,availableOnly,specName,specValue)
        @r.get('/brands')
        def brands(category:int|None=Query(default=None,ge=1,le=5)): return service.getBrands(category)
        @r.post('/compare')
        def compare(body:Comparison,response:Response):
            if len(set(body.ids))>4: response.headers['X-Comparison-Warning']='Only the first four selected products are compared.'
            return service.compareProducts(body.ids)
        @r.get('/{articleID}/image')
        def image(articleID:int): return FileResponse(service.image(articleID),headers={'Cache-Control':'public,max-age=3600'})
        @r.get('/{articleID}')
        def details(articleID:int): return service.getDetails(articleID)

from fastapi import APIRouter, Request, UploadFile, File
from .security import identity, read_upload
from Model.application.contract.ICatalogAdministration import ICatalogAdministration
from Model.application.contract.IAccount import IAccount
from Model.application.dto.CatalogAdministration import ProductUpdate, CategoryUpdate


class CatalogAdminController:
    def __init__(self, service:ICatalogAdministration, accounts:IAccount):
        self.router = APIRouter(prefix='/api/staff/catalogue', tags=['Catalogue administration'])
        r = self.router
        @r.get('/products')
        def products(request:Request):
            identity(request,accounts,roles={'Admin'}); return service.listProducts()
        @r.post('/products',status_code=201)
        def create(body:ProductUpdate,request:Request):
            actor=identity(request,accounts,roles={'Admin'}); return service.saveProduct(body.model_dump(),actorID=actor['employeeID'])
        @r.put('/products/{articleID}')
        def update(articleID:int,body:ProductUpdate,request:Request):
            actor=identity(request,accounts,roles={'Admin'}); return service.saveProduct(body.model_dump(),articleID,actor['employeeID'])
        @r.delete('/products/{articleID}')
        def archive(articleID:int,request:Request):
            actor=identity(request,accounts,roles={'Admin'}); return service.archiveProduct(articleID,actor['employeeID'])
        @r.post('/products/{articleID}/image')
        async def image(articleID:int,request:Request,file:UploadFile=File(...)):
            identity(request,accounts,roles={'Admin'})
            return service.uploadImage(articleID,await read_upload(file,10*1024*1024))
        @r.get('/categories')
        def categories(request:Request):
            identity(request,accounts,roles={'Admin'}); return service.categories()
        @r.put('/categories/{categoryID}')
        def category(categoryID:int,body:CategoryUpdate,request:Request):
            actor=identity(request,accounts,roles={'Admin'}); return service.updateCategory(categoryID,body.model_dump(),actor['employeeID'])

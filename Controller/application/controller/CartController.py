from fastapi import APIRouter,Request
from pydantic import BaseModel,Field
from .security import identity
from Model.application.contract.ICart import ICart
from Model.application.contract.IAccount import IAccount
class CartChange(BaseModel):
    articleID:int=Field(gt=0)
    quantity:int=Field(ge=1,le=99)
class CartController:
    def __init__(self,service:ICart,accounts:IAccount):
        self.router=APIRouter(prefix='/api/cart',tags=['Cart']);r=self.router
        @r.get('')
        def get(request:Request): return service.getCart(identity(request,accounts,roles={'customer'})['customerID'])
        @r.post('/items')
        def add(body:CartChange,request:Request): return service.addItem(identity(request,accounts,roles={'customer'})['customerID'],body.articleID,body.quantity)
        @r.put('/items')
        def update(body:CartChange,request:Request): return service.changeQuantity(identity(request,accounts,roles={'customer'})['customerID'],body.articleID,body.quantity)
        @r.delete('/items/{articleID}')
        def delete(articleID:int,request:Request): return service.removeItem(identity(request,accounts,roles={'customer'})['customerID'],articleID)

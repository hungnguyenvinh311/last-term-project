from fastapi import APIRouter,Request
from pydantic import BaseModel,Field
from typing import Literal
from .security import identity
from Model.application.contract.ICheckout import ICheckout
from Model.application.contract.IAccount import IAccount
from Model.application.contract.IFulfilment import IFulfilment
class Checkout(BaseModel):
    paymentMethod:Literal['COD','ONLINE']
    shippingAddress:str=Field(min_length=5,max_length=500)
    recipientPhone:str=Field(min_length=8,max_length=30)
    prices:dict[str,float]
class OrderController:
    def __init__(self,service:ICheckout,fulfilment:IFulfilment,accounts:IAccount):
        self.router=APIRouter(prefix='/api/orders',tags=['Orders']);r=self.router
        @r.get('')
        def list_orders(request:Request): return service.listOrders(identity(request,accounts,roles={'customer'})['customerID'])
        @r.post('',status_code=201)
        def submit(body:Checkout,request:Request): return service.submitCheckout(identity(request,accounts,roles={'customer'})['customerID'],body.model_dump())
        @r.get('/{orderID}')
        def details(orderID:int,request:Request): return service.getOrder(identity(request,accounts,roles={'customer'})['customerID'],orderID)
        @r.get('/{orderID}/invoice')
        def invoice(orderID:int,request:Request): return service.getInvoice(identity(request,accounts,roles={'customer'})['customerID'],orderID)
        @r.post('/{orderID}/cancel')
        def cancel(orderID:int,request:Request): return service.cancelBeforePacking(identity(request,accounts,roles={'customer'})['customerID'],orderID)
        @r.post('/{orderID}/confirm-delivery')
        def confirm_delivery(orderID:int,request:Request):
            customerID=identity(request,accounts,roles={'customer'})['customerID']
            return fulfilment.confirmReceived(customerID,orderID)

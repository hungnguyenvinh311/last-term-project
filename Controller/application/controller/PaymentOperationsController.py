from decimal import Decimal
from fastapi import APIRouter,Request
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
from .security import identity
from Model.application.contract.IAccount import IAccount
from Model.application.contract.IOrderOperations import IOrderOperations
from Model.application.contract.IPayment import IPayment


class CODConfirmation(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    amount:Decimal=Field(ge=0,max_digits=18,decimal_places=2)
    trackingNumber:str=Field(min_length=1,max_length=100)
    reference:str=Field(min_length=3,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


class PaymentOperationsController:
    def __init__(self,service:IOrderOperations,accounts:IAccount,payment:IPayment):
        self.router=APIRouter(prefix='/api/staff/orders',tags=['Staff order operations']);r=self.router
        @r.get('/{orderID}')
        def details(orderID:int,request:Request):
            identity(request,accounts,roles={'Admin','Sales Staff','Warehouse Staff','Manager'});return service.details(orderID)
        @r.post('/{orderID}/cancel')
        def cancel(orderID:int,request:Request):
            actor=identity(request,accounts,roles={'Admin','Sales Staff'});return service.cancel(orderID,actor['employeeID'])
        @r.post('/{orderID}/cod-confirmation')
        def cod(orderID:int,body:CODConfirmation,request:Request):
            actor=identity(request,accounts,roles={'Admin','Sales Staff'})
            return service.confirmCOD(orderID,body.amount,body.trackingNumber,body.reference,actor['employeeID'])
        class OnlineResult(BaseModel):
            scenario:Literal['success','failure','pending']
            reference:str|None=Field(default=None,min_length=3,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
            eventKey:str|None=Field(default=None,min_length=8,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
        @r.post('/{orderID}/online-payment')
        def online(orderID:int,body:OnlineResult,request:Request):
            actor=identity(request,accounts,roles={'Admin','Sales Staff'})
            return payment.recordStaffVerifiedOnlineResult(orderID,body.scenario,actor['employeeID'],body.reference,body.eventKey)

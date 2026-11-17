from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Literal
from .security import identity
from .AccountController import Registration
from Model.application.contract.ICheckout import ICheckout
from Model.application.contract.IFulfilment import IFulfilment
from Model.application.contract.IAccount import IAccount


class StatusChange(BaseModel):
    status: Literal['Packing','Packed','Dispatched']


class ActiveChange(BaseModel):
    active: bool


class RoleChange(BaseModel):
    role: Literal['Admin','Sales Staff','Warehouse Staff','Manager']


class EmployeeRegistration(Registration):
    role: Literal['Admin','Sales Staff','Warehouse Staff','Manager']


class StaffController:
    def __init__(self, checkout: ICheckout, fulfilment: IFulfilment, accounts: IAccount):
        self.router = APIRouter(prefix='/api/staff', tags=['Staff'])
        r = self.router

        @r.get('/orders')
        def orders(request: Request):
            identity(request, accounts, roles={'Admin','Sales Staff','Warehouse Staff','Manager'})
            return checkout.staffOrders()

        @r.post('/orders/{orderID}/shipment')
        def shipment(orderID: int, request: Request):
            actor = identity(request, accounts, roles={'Admin','Warehouse Staff'})
            return fulfilment.createShipment(orderID, actor['employeeID'])

        @r.put('/orders/{orderID}/shipment')
        def status(orderID: int, body: StatusChange, request: Request):
            actor = identity(request, accounts, roles={'Admin','Warehouse Staff'})
            return fulfilment.updateStatus(orderID, body.status, actor['employeeID'])

        @r.get('/accounts')
        def list_accounts(request: Request):
            identity(request, accounts, roles={'Admin'})
            return accounts.listAccounts()

        @r.get('/accounts/{accountID}/customer-history')
        def customer_history(accountID: int, request: Request):
            identity(request, accounts, roles={'Admin'})
            return accounts.customerHistory(accountID)

        @r.post('/accounts', status_code=201)
        def create_staff(body: EmployeeRegistration, request: Request):
            actor = identity(request, accounts, roles={'Admin'})
            return accounts.createStaff(body.email, body.password, body.fullName, body.role, actor['employeeID'])

        @r.put('/accounts/{accountID}')
        def activate(accountID: int, body: ActiveChange, request: Request):
            actor = identity(request, accounts, roles={'Admin'})
            accounts.setActive(accountID, body.active, actor['employeeID'])
            return {'ok': True}

        @r.put('/accounts/{accountID}/role')
        def change_role(accountID: int, body: RoleChange, request: Request):
            actor = identity(request, accounts, roles={'Admin'})
            accounts.setRole(accountID, body.role, actor['employeeID'])
            return {'ok': True}

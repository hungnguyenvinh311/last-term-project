from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, ConfigDict
from .security import identity
from Model.application.contract.IInventory import IInventory
from Model.application.contract.IAccount import IAccount


class ReceiptItem(BaseModel):
    articleID: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100000)


class ReceiptBody(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    receiptNumber: str = Field(min_length=3, max_length=255)
    items: list[ReceiptItem] = Field(min_length=1, max_length=500)


class AdjustmentBody(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    delta: int = Field(ne=0, ge=-100000, le=100000)
    reason: str = Field(min_length=3, max_length=255)


class InventoryController:
    def __init__(self, service: IInventory, accounts: IAccount):
        self.router = APIRouter(prefix='/api/staff/inventory', tags=['Inventory'])
        r = self.router

        @r.get('')
        def stock(request: Request):
            identity(request, accounts, roles={'Admin', 'Warehouse Staff'})
            return service.listStock()

        @r.post('/receipts', status_code=201)
        def receive(body: ReceiptBody, request: Request):
            actor = identity(request, accounts, roles={'Admin', 'Warehouse Staff'})
            return service.receiveStock(body.receiptNumber,
                                        [item.model_dump() for item in body.items], actor['employeeID'])

        @r.post('/{articleID}/adjustments')
        def adjust(articleID: int, body: AdjustmentBody, request: Request):
            actor = identity(request, accounts, roles={'Admin', 'Warehouse Staff'})
            return service.adjustStock(articleID, body.delta, body.reason, actor['employeeID'])

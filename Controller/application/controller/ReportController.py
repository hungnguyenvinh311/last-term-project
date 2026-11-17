from datetime import date
from typing import Literal
from fastapi import APIRouter,Request,Response,Query
from .security import identity
from Model.application.contract.IReporting import IReporting
from Model.application.contract.IReportExport import IReportExport
from Model.application.contract.IAccount import IAccount


class ReportController:
    def __init__(self,service:IReporting,exporter:IReportExport,accounts:IAccount):
        self.router=APIRouter(prefix='/api/staff/reports',tags=['Reports'])
        @self.router.get('/sales')
        def sales(request:Request,start:date,end:date,status:Literal['AwaitingPayment','PaymentFailed','Expired','Confirmed','Packing','Packed','Dispatched','Delivered','Cancelled']|None=None,
                  paymentMethod:Literal['COD','ONLINE']|None=None,categoryID:int|None=Query(default=None,ge=1,le=5),brand:str|None=Query(default=None,max_length=120),format:Literal['json','csv','pdf']='json'):
            identity(request,accounts,roles={'Admin','Manager'})
            report=service.sales(start,end,status=status,paymentMethod=paymentMethod,categoryID=categoryID,brand=brand)
            if format=='json': return report
            return Response(exporter.export(report,format),media_type='text/csv; charset=utf-8' if format=='csv' else 'application/pdf',
                            headers={'Content-Disposition':f'attachment; filename="sales-{start}-{end}.{format}"'})

        @self.router.get('/inventory')
        def inventory(request:Request,start:date,end:date,categoryID:int|None=Query(default=None,ge=1,le=10000),
                      brand:str|None=Query(default=None,max_length=120),format:Literal['json','csv','pdf']='json'):
            identity(request,accounts,roles={'Admin','Manager'})
            report=service.inventory(start,end,categoryID=categoryID,brand=brand)
            if format=='json': return report
            return Response(exporter.export(report,format),media_type='text/csv; charset=utf-8' if format=='csv' else 'application/pdf',
                            headers={'Content-Disposition':f'attachment; filename="inventory-{start}-{end}.{format}"'})

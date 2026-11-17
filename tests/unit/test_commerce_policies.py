"""Independent policies and derived-artifact preservation; no database or model download."""
import json,csv
from io import StringIO
from datetime import date
from decimal import Decimal
import pytest
from Model.application.service.CheckoutPricingService import CheckoutPricingService
from Model.application.service.ReportingService import ReportingService
from Model.application.integration.storage.ReportExporter import ReportExporter
from Model.application.integration.storage.CatalogueArtifacts import CatalogueArtifacts

@pytest.mark.parametrize('fee',['0','30000','15.50'])
def test_pricing_uses_decimal_and_no_fee_for_empty_cart(monkeypatch,fee):
    monkeypatch.setenv('APP_DEMO_SHIPPING_FEE',fee)
    pricing=CheckoutPricingService()
    quote=pricing.calculate([{'price':Decimal('0.10'),'quantity':3}])
    assert quote['itemSubTotal']==Decimal('.30')
    assert quote['totalAmount']==Decimal('.30')+Decimal(fee)
    assert pricing.calculate([])['totalAmount']==0

@pytest.mark.parametrize('fee',['NaN','Infinity','-1','10000001','1.001'])
def test_invalid_fee_is_rejected(monkeypatch,fee):
    monkeypatch.setenv('APP_DEMO_SHIPPING_FEE',fee)
    with pytest.raises(ValueError): CheckoutPricingService().calculate([{'price':1,'quantity':1}])

def test_catalogue_artifacts_invalidates_affected_composites_keeps_source_and_backup(tmp_path):
    path=tmp_path/'data/detection_labels/manifest.json';path.parent.mkdir(parents=True)
    doc={'version':1,'images':{'one':{'targets':[{'articleIDs':[1,2]}]},'pair':{'targets':[{'articleIDs':[1]},{'articleIDs':[3]}]},'other':{'targets':[{'articleIDs':[4]}]}}}
    path.write_text(json.dumps(doc),encoding='utf-8');before=path.read_bytes()
    source=tmp_path/'photo.jpg';source.write_bytes(b'untouched')
    artifacts=CatalogueArtifacts(tmp_path);artifacts.invalidateLabels(1)
    assert set(json.loads(path.read_text())['images'])=={'other'}
    assert path.with_name('manifest.before_catalogue_edits.json').read_bytes()==before
    artifacts.invalidateLabels(4)
    assert path.with_name('manifest.before_catalogue_edits.json').read_bytes()==before and source.read_bytes()==b'untouched'

def test_report_excludes_pending_failed_and_cancelled_without_join_duplication():
    class DAO:
        def read(self,start,end):
            orders=[dict(orderID=i,status=status,paymentMethod=method,paymentStatus=payment,itemSubTotal=Decimal(300),discountAmount=Decimal(20),paymentAmount=Decimal(310)) for i,status,method,payment in [
                (1,'Confirmed','COD','UnpaidCOD'),(2,'Confirmed','ONLINE','Paid'),(3,'AwaitingPayment','ONLINE','Pending'),
                (4,'AwaitingPayment','ONLINE','Failed'),(5,'Cancelled','ONLINE','RefundRequired')]]
            items=[dict(orderID=i,articleID=j,categoryID=1,brand='Samsung',productNameSnapshot='Phone',quantity=1,unitPrice=Decimal(price)) for i in range(1,6) for j,price in [(1,100),(2,200)]]
            return orders,items
    r=ReportingService(DAO()).sales(date(2026,1,1),date(2026,1,1))
    assert r['orderCount']==5 and r['units']==2
    assert r['itemGrossSales']==300 and r['matchedOrdersNetMerchandise']==300 and r['matchedOrdersPaidAmount']==310
    assert len(r['topProducts'])==2

@pytest.mark.parametrize('name',['=1+1',' +SUM(A1:A2)','@IMPORT','-123'])
def test_csv_neutralizes_product_name_formula(name):
    report=dict(start=date.today(),end=date.today(),orderCount=1,units=1,itemGrossSales=1,matchedOrdersNetMerchandise=1,matchedOrdersPaidAmount=1,
                scope='test',topProducts=[dict(articleID=1,productName=name,brand='Test',categoryID=1,quantity=1,grossSales=1)])
    rows=list(csv.reader(StringIO(ReportExporter().export(report,'csv').decode('utf-8-sig'))))
    assert rows[-1][1]=="'"+name

def test_new_interfaces_match_implementations():
    import importlib
    pairs=[
        ('Model.application.contract.ICatalogAdministration','ICatalogAdministration','Model.application.service.CatalogAdministrationService','CatalogAdministrationService'),
        ('Model.application.contract.ICheckoutPricing','ICheckoutPricing','Model.application.service.CheckoutPricingService','CheckoutPricingService'),
        ('Model.application.contract.IOrderOperations','IOrderOperations','Model.application.service.OrderOperationsService','OrderOperationsService'),
        ('Model.application.contract.IReporting','IReporting','Model.application.service.ReportingService','ReportingService'),
        ('Model.application.contract.IReportExport','IReportExport','Model.application.integration.storage.ReportExporter','ReportExporter'),
        ('DAO.contract.CategoryDAO','CategoryDAO','DAO.application.dao.CategoryDAOImpl','CategoryDAOImpl'),
        ('DAO.contract.ReportDAO','ReportDAO','DAO.application.dao.ReportDAOImpl','ReportDAOImpl')]
    for module,name,impl,cls in pairs:
        contract=getattr(importlib.import_module(module),name);implementation=getattr(importlib.import_module(impl),cls)
        assert all(callable(getattr(implementation,n,None)) for n in vars(contract) if not n.startswith('_'))

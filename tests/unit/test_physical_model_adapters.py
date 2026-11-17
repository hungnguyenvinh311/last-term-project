from datetime import date
from decimal import Decimal
from contextlib import contextmanager

from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
from DAO.application.dao.CartDAOImpl import CartDAOImpl
from Model.application.errors import DomainError
from Model.application.service.ReportingService import ReportingService
import pytest


def test_product_dao_decodes_physical_text_json_fields():
    row = {
        'articleID': 12, 'categoryID': 3, 'productName': 'Tablet A', 'brand': 'Example',
        'price': Decimal('1000000.00'), 'currency': 'VND', 'isActive': 1,
        'technicalSpecs': '{"screenSize":"11 inch","description":"Sample"}',
        'warrantyTerms': 'Bảo hành 12 tháng', 'imagePath': '/media/a.jpg',
        'imageEmbedding': '[0.1,0.2]', 'textEmbedding': '[0.3,0.4]',
        'subCategory': 'Tablet', 'onHandQuantity': 5, 'availableQuantity': 4,
        'screenSize': '11 inch', 'stylusSupport': 1,
    }
    product = ProductDAOImpl(None)._product(row)
    assert product.technicalSpecs == {'screenSize': '11 inch', 'description': 'Sample', 'stylusSupport': 1}
    assert product.imageEmbedding == [0.1, 0.2]
    assert product.textEmbedding == [0.3, 0.4]
    assert product.description == 'Sample'
    assert product.availableQuantity == 4


def test_cart_dao_rejects_quantity_above_live_available_stock():
    class DB:
        def __init__(self):
            self.statements = []

        @contextmanager
        def transaction(self):
            yield object()

        def query(self, sql, params=(), connection=None, one=False):
            self.statements.append(sql)
            if 'SELECT cartId AS cartID' in sql:
                return {'cartID': 2, 'customerID': 7}
            if 'SELECT p.articleId,p.isActive,p.price' in sql:
                return {'articleId': 33, 'isActive': 1, 'price': Decimal('100'), 'availableQuantity': 2}
            if 'SELECT quantity FROM CartItem' in sql:
                return None
            return 1

    db = DB()
    with pytest.raises(DomainError, match='available stock'):
        CartDAOImpl(db).save(7, 33, 3)
    assert not any('INSERT INTO CartItem' in statement for statement in db.statements)


class SalesReportDAO:
    def read(self, start, end):
        orders = [
            dict(orderID=1, status='Delivered', paymentMethod='COD', paymentStatus='Paid',
                 itemSubTotal=Decimal('100'), paymentAmount=Decimal('100')),
            dict(orderID=2, status='Delivered', paymentMethod='COD', paymentStatus='UnpaidCOD',
                 itemSubTotal=Decimal('200'), paymentAmount=Decimal('200')),
            dict(orderID=3, status='Confirmed', paymentMethod='ONLINE', paymentStatus='Paid',
                 itemSubTotal=Decimal('300'), paymentAmount=Decimal('300')),
            dict(orderID=4, status='Cancelled', paymentMethod='ONLINE', paymentStatus='Paid',
                 itemSubTotal=Decimal('400'), paymentAmount=Decimal('400')),
        ]
        items = [
            dict(orderID=1, articleID=1, quantity=1, unitPrice=Decimal('100'), productNameSnapshot='COD paid',
                 categoryID=1, brand='B'),
            dict(orderID=2, articleID=2, quantity=1, unitPrice=Decimal('200'), productNameSnapshot='COD unpaid',
                 categoryID=1, brand='B'),
            dict(orderID=3, articleID=3, quantity=1, unitPrice=Decimal('300'), productNameSnapshot='Online paid',
                 categoryID=1, brand='B'),
            dict(orderID=4, articleID=4, quantity=1, unitPrice=Decimal('400'), productNameSnapshot='Cancelled',
                 categoryID=1, brand='B'),
        ]
        return orders, items


def test_sales_report_counts_paid_orders_only_and_excludes_cancelled_sales():
    report = ReportingService(SalesReportDAO()).sales(date(2026, 1, 1), date(2026, 1, 1))
    assert report['units'] == 2
    assert report['itemGrossSales'] == Decimal('400')
    assert report['matchedOrdersNetMerchandise'] == Decimal('400')
    assert report['matchedOrdersPaidAmount'] == Decimal('400')

from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal
from Model.application.config.brands import brand_key, canonical_brand
from DAO.contract.ReportDAO import ReportDAO
from Model.application.errors import DomainError


class ReportingService:
    def __init__(self, dao: ReportDAO):
        self.dao = dao

    @staticmethod
    def _period(start, end):
        if end < start or (end - start).days > 366:
            raise DomainError('Report range must be from 1 to 367 days')
        return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)

    def sales(self, start, end, status=None, paymentMethod=None, categoryID=None, brand=None):
        start_at, end_at = self._period(start, end)
        orders, items = self.dao.read(start_at, end_at)
        orders = [o for o in orders if (not status or o['status'] == status)
                  and (not paymentMethod or o['paymentMethod'] == paymentMethod)]
        ordermap = {o['orderID']: o for o in orders}
        items = [i for i in items if i['orderID'] in ordermap
                 and (not categoryID or i['categoryID'] == categoryID)
                 and (not brand or brand_key(i['brand']) == brand_key(brand))]
        if categoryID or brand:
            matched = {i['orderID'] for i in items}
            orders = [o for o in orders if o['orderID'] in matched]
        def confirmed(order):
            return order['status'] in {'Confirmed','Packing','Packed','Dispatched','Delivered'} and (
                order['paymentStatus'] == 'Paid')
        sold = [item for item in items if confirmed(ordermap[item['orderID']])]
        products = {}
        for item in sold:
            product = products.setdefault(item['articleID'], dict(articleID=item['articleID'],
                productName=item['productNameSnapshot'],brand=canonical_brand(item['brand']),
                categoryID=item['categoryID'],quantity=0,grossSales=Decimal(0)))
            product['quantity'] += item['quantity']
            product['grossSales'] += item['unitPrice'] * item['quantity']
        return dict(start=start,end=end,timezone='Asia/Ho_Chi_Minh (UTC+07:00)',currency='VND',
            orderCount=len(orders),statusCounts=dict(Counter(o['status'] for o in orders)),
            units=sum(i['quantity'] for i in sold),
            itemGrossSales=sum((i['unitPrice']*i['quantity'] for i in sold),Decimal(0)),
            matchedOrdersNetMerchandise=sum((o['itemSubTotal'] for o in orders if confirmed(o)),Decimal(0)),
            matchedOrdersPaidAmount=sum((o['paymentAmount'] for o in orders if o['paymentStatus']=='Paid'
                                         and o['status']!='Cancelled'),Decimal(0)),
            topProducts=sorted(products.values(),key=lambda p:(-p['grossSales'],p['articleID'])),
            scope='Sales include paid orders only (COD is counted after staff confirms collection); item totals are grouped by the current product brand and category. Shipping is excluded from item sales.')

    def inventory(self, start, end, categoryID=None, brand=None):
        start_at, end_at = self._period(start, end)
        rows, movements = self.dao.inventoryRead(start_at, end_at, categoryID=categoryID)
        if brand:
            rows = [r for r in rows if brand_key(r['brand']) == brand_key(brand)]
        article_ids = {r['articleID'] for r in rows}
        movements = [m for m in movements if m['articleID'] in article_ids]
        for row in rows:
            row['brand'] = canonical_brand(row['brand'])
            row['closingQuantity'] = (row['openingQuantity'] + row['receivedInPeriod']
                                      + row['adjustmentsInPeriod'] - row['dispatchedInPeriod'])
            row['currentAvailableQuantity'] = max(0, row['onHandQuantity'] - row['committedQuantity'])
        totals = {key: sum(int(row[key] or 0) for row in rows) for key in
                  ('openingQuantity','receivedInPeriod','dispatchedInPeriod','adjustmentsInPeriod',
                   'closingQuantity','onHandQuantity','committedQuantity','currentAvailableQuantity')}
        return dict(start=start,end=end,timezone='Asia/Ho_Chi_Minh (UTC+07:00)',
                    productCount=len(rows),totals=totals,products=rows,movements=movements,
                    scope='Closing stock is calculated from the movement ledger for the selected period; current available quantity subtracts active holds and allocations.')

import json
import secrets
from datetime import datetime
from decimal import Decimal
from Model.application.errors import DomainError
from Model.application.contract.ICheckoutPricing import ICheckoutPricing


class OrderDAOImpl:
    def __init__(self, db, cartDAO, pricing: ICheckoutPricing):
        self.db, self.cartDAO, self.pricing = db, cartDAO, pricing

    _ORDER = """SELECT o.orderId AS orderID,o.customerId AS customerID,o.orderNumber,
                       o.placedAt AS createdAt,o.placedAt,o.status,o.totalAmount,o.shippingFee,
                       o.shippingAddress,o.shippingMethod,o.paymentMethod,o.holdExpiresAt,o.packedAt,
                       (SELECT u.phoneNumber FROM `User` u WHERE u.userId=o.customerId) AS recipientPhone,
                       COALESCE((SELECT SUM(oi.unitPrice*oi.quantity) FROM OrderItem oi WHERE oi.orderId=o.orderId),0) AS itemSubTotal,
                       0 AS discountAmount
                FROM `Order` o"""

    def findById(self, orderID, connection=None):
        row = self.db.query(self._ORDER + ' WHERE o.orderId=%s', (orderID,), connection, True)
        if row:
            row['items'] = self.db.query(
                """SELECT orderItemId AS orderItemID,orderId AS orderID,articleId AS articleID,
                          quantity,unitPrice,productNameSnapshot,specificationSnapshot,warrantySnapshot
                   FROM OrderItem WHERE orderId=%s ORDER BY orderItemId""",
                (orderID,), connection)
            payment = self.db.query('SELECT paymentId AS paymentID,orderId AS orderID,amount,status,transactionCode '
                                    'FROM Payment WHERE orderId=%s', (orderID,), connection, True)
            row['payment'] = payment
            row['currency'] = 'VND'
        return row

    def findOwned(self, customerID, orderID):
        row = self.findById(orderID)
        if not row or row['customerID'] != customerID:
            raise DomainError('Order not found', 404)
        return row

    def getInvoice(self, orderID, customerID=None):
        row = self.db.query(
            """SELECT inv.invoiceId AS invoiceID,inv.invoiceNumber,inv.issuedAt,inv.totalAmount,
                      o.orderId AS orderID,o.orderNumber,o.placedAt,o.shippingFee,o.shippingAddress,
                      u.fullName,u.phoneNumber,a.email,o.customerId AS customerID
               FROM Invoice inv JOIN `Order` o ON o.orderId=inv.orderId
               JOIN Customer c ON c.userId=o.customerId JOIN `User` u ON u.userId=c.userId
               LEFT JOIN Account a ON a.userId=c.userId
               WHERE inv.orderId=%s""" + (' AND o.customerId=%s' if customerID is not None else ''),
            (orderID, customerID) if customerID is not None else (orderID,), one=True)
        if not row:
            raise DomainError('Invoice not found', 404)
        row['items'] = self.db.query(
            """SELECT articleId AS articleID,productNameSnapshot,quantity,unitPrice,
                      warrantySnapshot,specificationSnapshot
               FROM OrderItem WHERE orderId=%s ORDER BY orderItemId""", (orderID,))
        row['currency'] = 'VND'
        return row

    def listOwned(self, customerID):
        self.expireHolds()
        return self.db.query(self._ORDER + ' WHERE o.customerId=%s ORDER BY o.placedAt DESC,o.orderId DESC',
                             (customerID,))

    def listAll(self):
        self.expireHolds()
        return self.db.query(
            self._ORDER + """ JOIN Customer c ON c.userId=o.customerId
                JOIN `User` u ON u.userId=c.userId
                LEFT JOIN Payment p ON p.orderId=o.orderId
                LEFT JOIN Shipment s ON s.orderId=o.orderId
                ORDER BY o.placedAt DESC,o.orderId DESC LIMIT 500""")

    def createWithItems(self, customerID, payload, actorID=None):
        self.expireHolds()
        with self.db.transaction() as c:
            cart = self.cartDAO.findForUpdate(customerID, c)
            rows = self.db.query(
                """SELECT p.articleId AS articleID,p.productName,p.brand,p.price,p.isActive,
                          p.technicalSpecs,p.warrantyTerms,ci.quantity
                   FROM CartItem ci JOIN Product p ON p.articleId=ci.articleId
                   WHERE ci.cartId=%s ORDER BY p.articleId FOR UPDATE""",
                (cart['cartID'],), c)
            if not rows:
                raise DomainError('Cart is empty', 409)
            if any(not p['isActive'] for p in rows):
                raise DomainError('Cart contains an unavailable product', 409)
            expected = payload.get('prices', {})
            if any(str(p['articleID']) not in expected or
                   Decimal(str(expected[str(p['articleID'])])) != p['price'] for p in rows):
                raise DomainError('A product price changed; review the cart and retry', 409)
            for product in rows:
                inventory = self.db.query('SELECT onHandQuantity FROM Inventory WHERE articleId=%s FOR UPDATE',
                                          (product['articleID'],), c, True)
                held = self.db.query("""SELECT COALESCE(SUM(quantity),0) AS quantity FROM StockCommitment
                                       WHERE inventoryArticleId=%s AND (status='ALLOCATED' OR
                                         (status='HELD' AND (expiresAt IS NULL OR expiresAt>UTC_TIMESTAMP())))""",
                                     (product['articleID'],), c, True)['quantity']
                if not inventory or inventory['onHandQuantity'] - held < product['quantity']:
                    raise DomainError(f"Insufficient available stock for article {product['articleID']}", 409)
            quote = self.pricing.calculate(rows)
            total = quote['totalAmount']
            method = payload['paymentMethod']
            recipient_phone = str(payload.get('recipientPhone', '')).strip()
            if recipient_phone:
                self.db.query('UPDATE `User` SET phoneNumber=%s WHERE userId=%s',
                              (recipient_phone, customerID), c)
            status = 'Confirmed' if method == 'COD' else 'AwaitingPayment'
            number = 'ORD' + datetime.utcnow().strftime('%Y%m%d%H%M%S') + secrets.token_hex(3).upper()
            hold = method == 'ONLINE'
            orderID = self.db.query(
                """INSERT INTO `Order`(customerId,orderNumber,placedAt,status,totalAmount,shippingFee,
                       shippingAddress,shippingMethod,paymentMethod,holdExpiresAt)
                   VALUES(%s,%s,UTC_TIMESTAMP(),%s,%s,%s,%s,%s,%s,
                       IF(%s=1,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 15 MINUTE),NULL))""",
                (customerID, number, status, total, quote['shippingFee'], payload['shippingAddress'],
                 payload.get('shippingMethod', 'Simulated'), method, int(hold)), c)
            for product in rows:
                self.db.query(
                    """INSERT INTO OrderItem(orderId,articleId,quantity,unitPrice,productNameSnapshot,
                           specificationSnapshot,warrantySnapshot) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (orderID, product['articleID'], product['quantity'], product['price'],
                     product['productName'], json.dumps(product['technicalSpecs'], ensure_ascii=False),
                     product['warrantyTerms']), c)
                self.db.query(
                    """INSERT INTO StockCommitment(orderId,inventoryArticleId,quantity,status,expiresAt)
                       VALUES(%s,%s,%s,%s,IF(%s=1,DATE_ADD(UTC_TIMESTAMP(),INTERVAL 15 MINUTE),NULL))""",
                    (orderID, product['articleID'], product['quantity'],
                     'ALLOCATED' if method == 'COD' else 'HELD', int(hold)), c)
            self.db.query('INSERT INTO Payment(orderId,amount,status,transactionCode) VALUES(%s,%s,%s,\'\')',
                          (orderID, total, 'UnpaidCOD' if method == 'COD' else 'Pending'), c)
            invoice_number = f'INV-{number}'
            self.db.query('INSERT INTO Invoice(orderId,invoiceNumber,issuedAt,totalAmount) '
                          'VALUES(%s,%s,UTC_TIMESTAMP(),%s)', (orderID, invoice_number, total), c)
            self.db.query('DELETE FROM CartItem WHERE cartId=%s', (cart['cartID'],), c)
            self._audit(c, actorID, 'ORDER_CREATED', f'Order:{orderID}', '', number)
        return self.findById(orderID)

    def updateVersioned(self, orderID, status, version=None):
        with self.db.transaction() as c:
            row = self.db.query('SELECT orderId,status FROM `Order` WHERE orderId=%s FOR UPDATE',
                                (orderID,), c, True)
            if not row:
                raise DomainError('Order not found', 404)
            self.db.query('UPDATE `Order` SET status=%s WHERE orderId=%s', (status, orderID), c)

    def cancel(self, customerID, orderID, actorID=None):
        with self.db.transaction() as c:
            row = self.db.query('SELECT * FROM `Order` WHERE orderId=%s AND customerId=%s FOR UPDATE',
                                (orderID, customerID), c, True)
            if not row:
                raise DomainError('Order not found', 404)
            if row['status'] == 'Cancelled':
                return
            if row['status'] not in {'Confirmed', 'AwaitingPayment'}:
                raise DomainError('Order can only be cancelled before packing', 409)
            self.db.query("UPDATE `Order` SET status='Cancelled',holdExpiresAt=NULL WHERE orderId=%s", (orderID,), c)
            self.db.query("UPDATE StockCommitment SET status='RELEASED',expiresAt=NULL "
                          "WHERE orderId=%s AND status IN ('HELD','ALLOCATED')", (orderID,), c)
            self.db.query("UPDATE Payment SET status=CASE WHEN status='Paid' THEN 'RefundRequired' "
                          "WHEN status='Pending' AND transactionCode<>'' THEN 'PendingReview' ELSE 'Cancelled' END "
                          'WHERE orderId=%s', (orderID,), c)
            self.db.query("UPDATE Shipment SET status='Cancelled' WHERE orderId=%s", (orderID,), c)
            self._audit(c, actorID, 'ORDER_CANCELLED', f'Order:{orderID}', row['status'], 'Cancelled')

    def expireHolds(self):
        with self.db.transaction() as c:
            rows = self.db.query(
                """SELECT commitmentId,orderId FROM StockCommitment
                   WHERE status='HELD' AND expiresAt IS NOT NULL AND expiresAt<=UTC_TIMESTAMP()
                   FOR UPDATE""", (), c)
            by_order = {}
            for item in rows:
                by_order.setdefault(item['orderId'], []).append(item['commitmentId'])
            for orderID, commitment_ids in by_order.items():
                for commitmentID in commitment_ids:
                    self.db.query("UPDATE StockCommitment SET status='RELEASED' WHERE commitmentId=%s",
                                  (commitmentID,), c)
                still_held = self.db.query("SELECT COUNT(*) AS n FROM StockCommitment WHERE orderId=%s AND status='HELD'",
                                           (orderID,), c, True)['n']
                if not still_held:
                    self.db.query("UPDATE `Order` SET status='Expired',holdExpiresAt=NULL "
                                  "WHERE orderId=%s AND status='AwaitingPayment'", (orderID,), c)
                    self.db.query("UPDATE Payment SET status='Expired' WHERE orderId=%s AND status='Pending'",
                                  (orderID,), c)

    def _audit(self, c, actorID, action, target, before, after):
        if actorID is not None:
            self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                          'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)',
                          (actorID, action, target, str(before or ''), str(after or '')), c)

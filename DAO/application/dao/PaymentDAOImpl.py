import secrets
import mysql.connector
from Model.application.errors import DomainError


class PaymentDAOImpl:
    def __init__(self, db):
        self.db = db

    def findByOrder(self, orderID):
        return self.db.query(
            """SELECT p.paymentId AS paymentID,p.orderId AS orderID,o.paymentMethod,
                      p.amount,p.status,p.transactionCode,
                      (SELECT MAX(pe.recordedAt) FROM PaymentEvent pe WHERE pe.paymentId=p.paymentId
                        AND pe.result='Paid') AS paidAt
               FROM Payment p JOIN `Order` o ON o.orderId=p.orderId WHERE p.orderId=%s""",
            (orderID,), one=True)

    def confirmCOD(self, orderID, amount, trackingNumber, reference, actorID=None):
        already_confirmed = False
        try:
            with self.db.transaction() as c:
                order = self.db.query('SELECT * FROM `Order` WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
                payment = self.db.query('SELECT * FROM Payment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
                shipment = self.db.query('SELECT * FROM Shipment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
                if not order or not payment:
                    raise DomainError('Payment or order not found', 404)
                if order['paymentMethod'] != 'COD' or order['status'] != 'Delivered' or not shipment or shipment['status'] != 'Delivered':
                    raise DomainError('COD can only be confirmed for a delivered order', 409)
                if amount != order['totalAmount'] or amount != payment['amount'] or trackingNumber != shipment['trackingNumber']:
                    raise DomainError('Amount or tracking number does not match', 409)
                if payment['status'] == 'Paid':
                    if payment['transactionCode'] != reference:
                        raise DomainError('COD was already confirmed with another reference', 409)
                    already_confirmed = True
                elif payment['status'] != 'UnpaidCOD':
                    raise DomainError('COD payment is not awaiting confirmation', 409)
                else:
                    self.db.query("UPDATE Payment SET status='Paid',transactionCode=%s WHERE orderId=%s",
                                  (reference, orderID), c)
                    self._event(c, payment['paymentId'], actorID, 'Paid', reference, 'COD-' + reference)
                    self._audit(c, actorID, 'COD_PAYMENT_CONFIRMED', f'Order:{orderID}', 'UnpaidCOD', 'Paid')
        except mysql.connector.IntegrityError:
            raise DomainError('Payment reference has already been recorded', 409) from None
        return self.findByOrder(orderID)

    def saveSummary(self, orderID, outcome, actorID=None, reference=None, eventKey=None):
        reference = (reference or outcome.transactionCode or '').strip()
        eventKey = (eventKey or secrets.token_hex(12)).strip()
        if not reference or not eventKey:
            raise DomainError('Payment reference and event key are required')
        result = {'Paid':'Paid','Failed':'Failed','Pending':'PendingReview'}.get(outcome.status)
        if not result:
            raise DomainError('Unsupported payment result')
        replayed = False
        try:
            with self.db.transaction() as c:
                order = self.db.query('SELECT * FROM `Order` WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
                payment = self.db.query('SELECT * FROM Payment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
                if not order or not payment:
                    raise DomainError('Payment or order not found', 404)
                if order['status'] in {'Cancelled','Expired'}:
                    raise DomainError('Order is no longer payable', 409)
                if order['paymentMethod'] != 'ONLINE':
                    raise DomainError('This order is not an online payment', 409)
                if outcome.amount != order['totalAmount'] or outcome.orderID != orderID:
                    raise DomainError('Payment result does not match the order amount', 409)
                existing = self.db.query('SELECT * FROM PaymentEvent WHERE paymentId=%s AND eventKey=%s',
                                         (payment['paymentId'], eventKey), c, True)
                if existing:
                    if existing['result'] != result or existing['referenceCode'] != reference:
                        raise DomainError('Idempotency key was reused with different payment data', 409)
                    replayed = True
                elif payment['status'] == 'Paid':
                    raise DomainError('Payment was already confirmed', 409)
                else:
                    self._event(c, payment['paymentId'], actorID, result, reference, eventKey)
                    if result == 'Paid':
                        self.db.query("UPDATE Payment SET status='Paid',transactionCode=%s WHERE paymentId=%s",
                                      (reference, payment['paymentId']), c)
                        self.db.query("UPDATE `Order` SET status='Confirmed',holdExpiresAt=NULL WHERE orderId=%s",
                                      (orderID,), c)
                        self.db.query("UPDATE StockCommitment SET status='ALLOCATED',expiresAt=NULL "
                                      "WHERE orderId=%s AND status='HELD'", (orderID,), c)
                    elif result == 'Failed':
                        self.db.query("UPDATE Payment SET status='Failed',transactionCode=%s WHERE paymentId=%s",
                                      (reference, payment['paymentId']), c)
                        self.db.query("UPDATE `Order` SET status='PaymentFailed',holdExpiresAt=NULL WHERE orderId=%s",
                                      (orderID,), c)
                        self.db.query("UPDATE StockCommitment SET status='RELEASED',expiresAt=NULL "
                                      "WHERE orderId=%s AND status='HELD'", (orderID,), c)
                    else:
                        self.db.query("UPDATE Payment SET status='PendingReview',transactionCode=%s WHERE paymentId=%s",
                                      (reference, payment['paymentId']), c)
                    self._audit(c, actorID, 'ONLINE_PAYMENT_RESULT_RECORDED', f'Order:{orderID}',
                                payment['status'], result)
        except mysql.connector.IntegrityError:
            raise DomainError('Payment event has already been recorded', 409) from None
        return self.findByOrder(orderID)

    def _event(self, c, paymentID, actorID, result, reference, eventKey):
        self.db.query('INSERT INTO PaymentEvent(paymentId,employeeId,result,referenceCode,eventKey,recordedAt) '
                      'VALUES(%s,%s,%s,%s,%s,UTC_TIMESTAMP())',
                      (paymentID, actorID, result, reference, eventKey), c)

    def _audit(self, c, actorID, action, target, before, after):
        if actorID is not None:
            self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                          'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)',
                          (actorID, action, target, before, after), c)

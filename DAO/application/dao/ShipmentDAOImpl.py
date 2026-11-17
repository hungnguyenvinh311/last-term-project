from Model.application.errors import DomainError


class ShipmentDAOImpl:
    def __init__(self, db):
        self.db = db

    def findByOrder(self, orderID):
        return self.db.query(
            """SELECT shipmentId AS shipmentID,orderId AS orderID,trackingNumber,status,deliveredAt,
                      'Simulated shipping provider' AS carrier
               FROM Shipment WHERE orderId=%s""", (orderID,), one=True)

    def saveSummary(self, orderID, outcome, actorID=None):
        with self.db.transaction() as c:
            order = self.db.query('SELECT * FROM `Order` WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            if not order or order['status'] not in {'Confirmed','Packing','Packed'}:
                raise DomainError('Order is not ready for a shipment', 409)
            existing = self.db.query('SELECT * FROM Shipment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            if not existing:
                self.db.query("INSERT INTO Shipment(orderId,trackingNumber,status) VALUES(%s,%s,'Created')",
                              (orderID, outcome.trackingNumber), c)
                self._audit(c, actorID, 'SHIPMENT_CREATED', f'Order:{orderID}', '', outcome.trackingNumber)
        return self.findByOrder(orderID)

    def updateStatus(self, orderID, status, actorID=None):
        transitions = {'Confirmed':'Packing','Packing':'Packed','Packed':'Dispatched'}
        with self.db.transaction() as c:
            order = self.db.query('SELECT * FROM `Order` WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            shipment = self.db.query('SELECT * FROM Shipment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            if not order or not shipment:
                raise DomainError('Shipment not found', 404)
            if order['status'] != status and transitions.get(order['status']) != status:
                raise DomainError('Invalid order status transition', 409)
            if order['status'] != status and status == 'Dispatched':
                commitments = self.db.query(
                    "SELECT * FROM StockCommitment WHERE orderId=%s AND status='ALLOCATED' FOR UPDATE",
                    (orderID,), c)
                if not commitments:
                    raise DomainError('Order has no allocated stock', 409)
                for commitment in commitments:
                    inventory = self.db.query('SELECT onHandQuantity FROM Inventory WHERE articleId=%s FOR UPDATE',
                                              (commitment['inventoryArticleId'],), c, True)
                    if not inventory or inventory['onHandQuantity'] < commitment['quantity']:
                        raise DomainError('Physical stock is insufficient to dispatch the order', 409)
                    self.db.query('UPDATE Inventory SET onHandQuantity=onHandQuantity-%s WHERE articleId=%s',
                                  (commitment['quantity'], commitment['inventoryArticleId']), c)
                    self.db.query("UPDATE StockCommitment SET status='SHIPPED' WHERE commitmentId=%s",
                                  (commitment['commitmentId'],), c)
                    self.db.query("INSERT INTO StockMovement(inventoryArticleId,receiptId,quantity,type,reason,occurredAt) "
                                  "VALUES(%s,NULL,%s,'OUT',%s,UTC_TIMESTAMP())",
                                  (commitment['inventoryArticleId'], -commitment['quantity'],
                                   f'Order dispatch {order["orderNumber"]}'), c)
            if order['status'] != status:
                self.db.query('UPDATE `Order` SET status=%s,packedAt=IF(%s=\'Packed\',UTC_TIMESTAMP(),packedAt) '
                              'WHERE orderId=%s', (status, status, orderID), c)
                self.db.query('UPDATE Shipment SET status=%s WHERE orderId=%s', (status, orderID), c)
                self._audit(c, actorID, 'FULFILMENT_STATUS_CHANGED', f'Order:{orderID}', order['status'], status)
        return self.findByOrder(orderID)

    def confirmReceived(self, orderID, customerID):
        with self.db.transaction() as c:
            order = self.db.query('SELECT * FROM `Order` WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            if not order or order['customerId'] != customerID:
                raise DomainError('Order not found', 404)
            shipment = self.db.query('SELECT * FROM Shipment WHERE orderId=%s FOR UPDATE', (orderID,), c, True)
            if not shipment or order['status'] != 'Dispatched' or shipment['status'] != 'Dispatched':
                raise DomainError('Only a dispatched order can be confirmed as delivered', 409)
            self.db.query("UPDATE Shipment SET status='Delivered',deliveredAt=UTC_TIMESTAMP() WHERE orderId=%s",
                          (orderID,), c)
            self.db.query("UPDATE `Order` SET status='Delivered' WHERE orderId=%s", (orderID,), c)
        return self.findByOrder(orderID)

    def _audit(self, c, actorID, action, target, before, after):
        if actorID is not None:
            self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                          'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)',
                          (actorID, action, target, str(before or ''), str(after or '')), c)

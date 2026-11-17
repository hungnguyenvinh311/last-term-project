import mysql.connector
from Model.application.errors import DomainError


class InventoryDAOImpl:
    def __init__(self, db):
        self.db = db

    def listAll(self):
        return self.db.query(
            """SELECT p.articleId AS articleID,p.productName,p.brand,p.price,p.isActive,
                      cat.categoryId AS categoryID,cat.groupName,cat.subCategory,i.onHandQuantity,
                      COALESCE(SUM(CASE WHEN sc.status='ALLOCATED' OR (sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())) THEN sc.quantity ELSE 0 END),0) AS committedQuantity,
                      GREATEST(i.onHandQuantity-COALESCE(SUM(CASE WHEN sc.status='ALLOCATED' OR (sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())) THEN sc.quantity ELSE 0 END),0),0) AS availableQuantity
               FROM Inventory i JOIN Product p ON p.articleId=i.articleId
               JOIN Category cat ON cat.categoryId=p.categoryId
               LEFT JOIN StockCommitment sc ON sc.inventoryArticleId=i.articleId
               GROUP BY p.articleId,p.productName,p.brand,p.price,p.isActive,cat.categoryId,
                        cat.groupName,cat.subCategory,i.onHandQuantity
               ORDER BY cat.groupName,cat.subCategory,p.brand,p.productName""")

    def receive(self, receiptNumber, items, actorID):
        if not items:
            raise DomainError('At least one product is required')
        seen = set()
        for item in items:
            articleID, quantity = int(item['articleID']), int(item['quantity'])
            if articleID in seen or quantity <= 0:
                raise DomainError('Receipt must contain unique products with positive quantities')
            seen.add(articleID)
        try:
            with self.db.transaction() as c:
                receiptID = self.db.query('INSERT INTO StockReceipt(receiptNumber,receivedAt) '
                                          'VALUES(%s,UTC_TIMESTAMP())', (receiptNumber.strip(),), c)
                for item in items:
                    articleID, quantity = int(item['articleID']), int(item['quantity'])
                    inventory = self.db.query('SELECT onHandQuantity FROM Inventory WHERE articleId=%s FOR UPDATE',
                                              (articleID,), c, True)
                    if not inventory:
                        raise DomainError(f'Inventory record not found for product {articleID}', 404)
                    self.db.query('UPDATE Inventory SET onHandQuantity=onHandQuantity+%s WHERE articleId=%s',
                                  (quantity, articleID), c)
                    self.db.query("INSERT INTO StockMovement(inventoryArticleId,receiptId,quantity,type,reason,occurredAt) "
                                  "VALUES(%s,%s,%s,'IN',%s,UTC_TIMESTAMP())",
                                  (articleID, receiptID, quantity, f'Receipt {receiptNumber}'), c)
                    self._audit(c, actorID, 'STOCK_RECEIVED', f'Product:{articleID}',
                                str(inventory['onHandQuantity']), str(inventory['onHandQuantity'] + quantity))
        except mysql.connector.IntegrityError:
            raise DomainError('Receipt number already exists; stock was not applied twice', 409) from None
        return {'receiptID': receiptID, 'receiptNumber': receiptNumber, 'itemsProcessed': len(items)}

    def adjust(self, articleID, delta, reason, actorID):
        if not delta or not reason or len(reason.strip()) < 3:
            raise DomainError('A non-zero adjustment and a reason are required')
        with self.db.transaction() as c:
            inventory = self.db.query('SELECT onHandQuantity FROM Inventory WHERE articleId=%s FOR UPDATE',
                                      (articleID,), c, True)
            if not inventory:
                raise DomainError('Inventory record not found', 404)
            committed = self.db.query("SELECT COALESCE(SUM(quantity),0) AS quantity FROM StockCommitment "
                                      "WHERE inventoryArticleId=%s AND (status='ALLOCATED' OR "
                                      "(status='HELD' AND (expiresAt IS NULL OR expiresAt>UTC_TIMESTAMP())))",
                                      (articleID,), c, True)['quantity']
            updated = inventory['onHandQuantity'] + int(delta)
            if updated < committed or updated < 0:
                raise DomainError('Adjustment cannot reduce physical stock below committed quantity', 409)
            self.db.query('UPDATE Inventory SET onHandQuantity=%s WHERE articleId=%s', (updated, articleID), c)
            self.db.query("INSERT INTO StockMovement(inventoryArticleId,receiptId,quantity,type,reason,occurredAt) "
                          "VALUES(%s,NULL,%s,'ADJUSTMENT',%s,UTC_TIMESTAMP())",
                          (articleID, int(delta), reason.strip()), c)
            self._audit(c, actorID, 'STOCK_ADJUSTED', f'Product:{articleID}',
                        str(inventory['onHandQuantity']), str(updated))
        return {'articleID': articleID, 'onHandQuantity': updated, 'committedQuantity': committed,
                'availableQuantity': updated - committed}

    def _audit(self, c, actorID, action, target, before, after):
        self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                      'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)',
                      (actorID, action, target, before, after), c)

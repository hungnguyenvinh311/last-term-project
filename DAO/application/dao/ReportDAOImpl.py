class ReportDAOImpl:
    def __init__(self, db):
        self.db = db

    def read(self, start, end):
        with self.db.transaction() as c:
            orders = self.db.query(
                """SELECT o.orderId AS orderID,o.customerId AS customerID,o.orderNumber,
                          o.placedAt AS createdAt,o.status,o.totalAmount,o.shippingFee,
                          o.shippingAddress,o.shippingMethod,o.paymentMethod,
                          COALESCE((SELECT SUM(oi.unitPrice*oi.quantity) FROM OrderItem oi WHERE oi.orderId=o.orderId),0) AS itemSubTotal,
                          0 AS discountAmount,p.status AS paymentStatus,p.amount AS paymentAmount
                   FROM `Order` o LEFT JOIN Payment p ON p.orderId=o.orderId
                   WHERE o.placedAt>=%s AND o.placedAt<%s ORDER BY o.orderId""",
                (start, end), c)
            items = self.db.query(
                """SELECT i.orderItemId AS orderItemID,i.orderId AS orderID,i.articleId AS articleID,
                          i.quantity,i.unitPrice,i.productNameSnapshot,p.categoryId AS categoryID,p.brand
                   FROM OrderItem i JOIN `Order` o ON o.orderId=i.orderId
                   JOIN Product p ON p.articleId=i.articleId
                   WHERE o.placedAt>=%s AND o.placedAt<%s ORDER BY i.orderItemId""",
                (start, end), c)
        return orders, items

    def inventoryRead(self, start, end, categoryID=None, brand=None):
        where = ['p.isActive=1']
        params = []
        if categoryID:
            where.append('p.categoryId=%s')
            params.append(categoryID)
        if brand:
            where.append('p.brand=%s')
            params.append(brand)
        with self.db.transaction() as c:
            rows = self.db.query(
                """SELECT p.articleId AS articleID,p.productName,p.brand,p.categoryId AS categoryID,
                          cat.groupName,cat.subCategory,i.onHandQuantity,
                          COALESCE((SELECT SUM(sc.quantity) FROM StockCommitment sc
                            WHERE sc.inventoryArticleId=p.articleId AND (sc.status='ALLOCATED' OR (sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())))),0) AS committedQuantity,
                          COALESCE((SELECT SUM(sm.quantity) FROM StockMovement sm
                            WHERE sm.inventoryArticleId=p.articleId AND sm.occurredAt>=%s AND sm.occurredAt<%s
                              AND sm.type='IN'),0) AS receivedInPeriod,
                          COALESCE((SELECT SUM(ABS(sm.quantity)) FROM StockMovement sm
                            WHERE sm.inventoryArticleId=p.articleId AND sm.occurredAt>=%s AND sm.occurredAt<%s
                              AND sm.type='OUT'),0) AS dispatchedInPeriod,
                          COALESCE((SELECT SUM(sm.quantity) FROM StockMovement sm
                            WHERE sm.inventoryArticleId=p.articleId AND sm.occurredAt>=%s AND sm.occurredAt<%s
                              AND sm.type='ADJUSTMENT'),0) AS adjustmentsInPeriod,
                          i.onHandQuantity-COALESCE((SELECT SUM(sm.quantity) FROM StockMovement sm
                            WHERE sm.inventoryArticleId=p.articleId AND sm.occurredAt>=%s AND sm.type IN ('IN','OUT','ADJUSTMENT')),0) AS openingQuantity
                   FROM Product p JOIN Category cat ON cat.categoryId=p.categoryId
                   JOIN Inventory i ON i.articleId=p.articleId
                   WHERE """ + ' AND '.join(where) + ' ORDER BY cat.groupName,cat.subCategory,p.brand,p.productName',
                (start, end, start, end, start, end, end, *params), c)
            movements = self.db.query(
                """SELECT sm.movementId AS movementID,sm.inventoryArticleId AS articleID,
                          p.productName,p.brand,cat.subCategory,sm.quantity,sm.type,sm.reason,sm.occurredAt
                   FROM StockMovement sm JOIN Product p ON p.articleId=sm.inventoryArticleId
                   JOIN Category cat ON cat.categoryId=p.categoryId
                   WHERE sm.occurredAt>=%s AND sm.occurredAt<%s
                   ORDER BY sm.occurredAt,sm.movementId""", (start, end), c)
        return rows, movements

from Model.application.errors import DomainError


class CartDAOImpl:
    def __init__(self, db):
        self.db = db

    def findForUpdate(self, customerID, connection):
        self.db.query('INSERT INTO Cart(customerId,createdAt) VALUES(%s,UTC_TIMESTAMP()) '
                      'ON DUPLICATE KEY UPDATE customerId=VALUES(customerId)', (customerID,), connection)
        return self.db.query('SELECT cartId AS cartID,customerId AS customerID FROM Cart '
                             'WHERE customerId=%s FOR UPDATE', (customerID,), connection, True)

    def getCart(self, customerID):
        rows = self.db.query(
            """SELECT p.articleId AS articleID,p.productName,p.price,'VND' AS currency,p.imagePath,
                      p.isActive,ci.quantity,
                      GREATEST(COALESCE(i.onHandQuantity,0)-COALESCE((SELECT SUM(sc.quantity)
                        FROM StockCommitment sc WHERE sc.inventoryArticleId=p.articleId
                        AND (sc.status='ALLOCATED' OR (sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())))),0),0) AS availableQuantity
               FROM Cart c JOIN CartItem ci ON ci.cartId=c.cartId
               JOIN Product p ON p.articleId=ci.articleId
               LEFT JOIN Inventory i ON i.articleId=p.articleId
               WHERE c.customerId=%s ORDER BY ci.cartItemId""", (customerID,))
        return {'items': rows, 'total': sum((r['price'] or 0) * r['quantity'] for r in rows)}

    def save(self, customerID, articleID, quantity, add=False):
        with self.db.transaction() as c:
            cart = self.findForUpdate(customerID, c)
            product = self.db.query(
                """SELECT p.articleId,p.isActive,p.price,
                          GREATEST(COALESCE(i.onHandQuantity,0)-COALESCE((SELECT SUM(sc.quantity)
                            FROM StockCommitment sc WHERE sc.inventoryArticleId=p.articleId
                            AND (sc.status='ALLOCATED' OR (sc.status='HELD' AND
                                 (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())))),0),0) AS availableQuantity
                   FROM Product p LEFT JOIN Inventory i ON i.articleId=p.articleId WHERE p.articleId=%s""",
                (articleID,), c, True)
            if quantity and (not product or not product['isActive']):
                raise DomainError('Product is not available', 404)
            old = self.db.query('SELECT quantity FROM CartItem WHERE cartId=%s AND articleId=%s',
                                (cart['cartID'], articleID), c, True)
            value = quantity + (old['quantity'] if old and add else 0)
            if not 0 <= value <= 99:
                raise DomainError('Quantity must be between 1 and 99')
            if value > (product or {}).get('availableQuantity', 0):
                raise DomainError('Requested quantity exceeds currently available stock', 409)
            if value == 0:
                self.db.query('DELETE FROM CartItem WHERE cartId=%s AND articleId=%s',
                              (cart['cartID'], articleID), c)
            else:
                self.db.query('INSERT INTO CartItem(cartId,articleId,quantity) VALUES(%s,%s,%s) '
                              'ON DUPLICATE KEY UPDATE quantity=VALUES(quantity)',
                              (cart['cartID'], articleID, value), c)
        return self.getCart(customerID)

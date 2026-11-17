import secrets
import mysql.connector
from Model.application.errors import DomainError


class AccountDAOImpl:
    """Persistence for Account, User, Customer, Employee and AuthSession."""

    def __init__(self, db):
        self.db = db

    def register(self, email, passwordHash, fullName, role='customer', phoneNumber='', actorID=None):
        if role not in {'customer', 'Admin', 'Sales Staff', 'Warehouse Staff', 'Manager'}:
            raise DomainError('Unsupported account role')
        try:
            with self.db.transaction() as c:
                user_id = self.db.query(
                    'INSERT INTO `User`(fullName,phoneNumber) VALUES(%s,%s)',
                    (fullName, phoneNumber), c)
                if role == 'customer':
                    self.db.query('INSERT INTO Customer(userId,registeredAt) VALUES(%s,NOW())', (user_id,), c)
                else:
                    code = f'EMP-{user_id:06d}-{secrets.token_hex(2).upper()}'
                    self.db.query('INSERT INTO Employee(userId,employeeCode,role) VALUES(%s,%s,%s)',
                                  (user_id, code, role), c)
                account_id = self.db.query(
                    'INSERT INTO Account(userId,email,passwordHash,isActive) VALUES(%s,%s,%s,1)',
                    (user_id, email, passwordHash), c)
                if actorID is not None:
                    self._audit(c, actorID, 'EMPLOYEE_ACCOUNT_CREATED', f'Account:{account_id}', '', role)
            return {'accountID': account_id, 'customerID': user_id if role == 'customer' else None,
                    'employeeID': user_id if role != 'customer' else None, 'userID': user_id,
                    'email': email, 'role': role, 'isActive': True}
        except mysql.connector.IntegrityError:
            raise DomainError('Email is already registered', 409) from None

    def findByEmail(self, email):
        return self.db.query(
            """SELECT a.accountId AS accountID,a.userId AS userID,a.email,a.passwordHash,a.isActive,
                      COALESCE(e.role,'customer') AS role,
                      IF(c.userId IS NULL,NULL,a.userId) AS customerID,
                      IF(e.userId IS NULL,NULL,a.userId) AS employeeID,
                      u.fullName,u.phoneNumber
               FROM Account a JOIN `User` u ON u.userId=a.userId
               LEFT JOIN Customer c ON c.userId=a.userId
               LEFT JOIN Employee e ON e.userId=a.userId
               WHERE a.email=%s""", (email,), one=True)

    def createSession(self, tokenHash, accountID, hours):
        self.db.query(
            'INSERT INTO AuthSession(tokenHash,accountId,createdAt,expiresAt) '
            'VALUES(%s,%s,UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL %s HOUR))',
            (tokenHash, accountID, hours))

    def findSession(self, tokenHash):
        return self.db.query(
            """SELECT a.accountId AS accountID,a.userId AS userID,a.email,a.isActive,
                      COALESCE(e.role,'customer') AS role,
                      IF(c.userId IS NULL,NULL,a.userId) AS customerID,
                      IF(e.userId IS NULL,NULL,a.userId) AS employeeID,u.fullName,u.phoneNumber
               FROM Account a JOIN AuthSession s ON s.accountId=a.accountId
               JOIN `User` u ON u.userId=a.userId
               LEFT JOIN Customer c ON c.userId=a.userId
               LEFT JOIN Employee e ON e.userId=a.userId
               WHERE s.tokenHash=%s AND s.expiresAt>UTC_TIMESTAMP() AND a.isActive=1""",
            (tokenHash,), one=True)

    def deleteSession(self, tokenHash):
        self.db.query('DELETE FROM AuthSession WHERE tokenHash=%s', (tokenHash,))

    def listAccounts(self):
        return self.db.query(
            """SELECT a.accountId AS accountID,a.userId AS userID,a.email,a.isActive,
                      COALESCE(e.role,'customer') AS role,
                      IF(c.userId IS NULL,NULL,a.userId) AS customerID,
                      u.fullName,u.phoneNumber
               FROM Account a JOIN `User` u ON u.userId=a.userId
               LEFT JOIN Customer c ON c.userId=a.userId
               LEFT JOIN Employee e ON e.userId=a.userId
               ORDER BY a.accountId DESC""")

    def customerHistory(self, accountID):
        account = self.db.query(
            """SELECT a.accountId AS accountID,a.userId AS customerID,a.email,a.isActive,
                      u.fullName,u.phoneNumber,c.dateOfBirth
               FROM Account a JOIN `User` u ON u.userId=a.userId
               JOIN Customer c ON c.userId=a.userId WHERE a.accountId=%s""",
            (accountID,), one=True)
        if not account:
            raise DomainError('Customer account not found', 404)
        orders = self.db.query(
            """SELECT o.orderId AS orderID,o.orderNumber,o.status,o.paymentMethod,o.totalAmount,
                      o.placedAt AS createdAt,p.status AS paymentStatus,p.amount AS paidAmount,
                      s.status AS shipmentStatus,s.deliveredAt,
                      (SELECT GROUP_CONCAT(CONCAT(i.productNameSnapshot,' x ',i.quantity)
                        ORDER BY i.orderItemId SEPARATOR '; ')
                       FROM OrderItem i WHERE i.orderId=o.orderId) AS itemSummary
               FROM `Order` o LEFT JOIN Payment p ON p.orderId=o.orderId
               LEFT JOIN Shipment s ON s.orderId=o.orderId
               WHERE o.customerId=%s ORDER BY o.placedAt DESC,o.orderId DESC""",
            (account['customerID'],))
        total = self.db.query(
            """SELECT COALESCE(SUM(p.amount),0) AS total
               FROM `Order` o JOIN Payment p ON p.orderId=o.orderId
               WHERE o.customerId=%s AND o.status='Delivered' AND p.status='Paid'""",
            (account['customerID'],), one=True)['total']
        return {'customer': account, 'orders': orders, 'totalPaidDelivered': total}

    def setActive(self, accountID, active, actorID=None):
        with self.db.transaction() as c:
            row = self.db.query(
                'SELECT accountId,userId FROM Account WHERE accountId=%s FOR UPDATE',
                (accountID,), c, True)
            if not row:
                raise DomainError('Account not found', 404)
            if row['userId'] == actorID:
                raise DomainError('You cannot deactivate your own account', 403)
            self.db.query('UPDATE Account SET isActive=%s WHERE accountId=%s',
                          (bool(active), accountID), c)
            if not active:
                self.db.query('DELETE FROM AuthSession WHERE accountId=%s', (accountID,), c)
            self._audit(c, actorID, 'ACCOUNT_STATUS_CHANGED', f'Account:{accountID}',
                        str(not bool(active)), str(bool(active)))

    def setRole(self, accountID, role, actorID):
        if role not in {'Admin','Sales Staff','Warehouse Staff','Manager'}:
            raise DomainError('Unsupported employee role')
        with self.db.transaction() as c:
            employee = self.db.query('SELECT e.userId,e.role,a.accountId FROM Employee e '
                                      'JOIN Account a ON a.userId=e.userId WHERE a.accountId=%s FOR UPDATE',
                                      (accountID,), c, True)
            if not employee:
                raise DomainError('Account is not an employee account', 409)
            if employee['userId'] == actorID:
                raise DomainError('You cannot change your own role', 403)
            self.db.query('UPDATE Employee SET role=%s WHERE userId=%s', (role, employee['userId']), c)
            self._audit(c, actorID, 'EMPLOYEE_ROLE_CHANGED', f'Account:{accountID}', employee['role'], role)

    def _audit(self, connection, employeeID, action, target, beforeValue, afterValue):
        if employeeID is None:
            return
        self.db.query(
            """INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue)
               VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)""",
            (employeeID, action, target, beforeValue or '', afterValue or ''), connection)

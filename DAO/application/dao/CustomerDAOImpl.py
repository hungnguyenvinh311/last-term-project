from Model.application.errors import DomainError


class CustomerDAOImpl:
    def __init__(self, db):
        self.db = db

    def findById(self, customerID):
        return self.db.query(
            """SELECT c.userId AS customerID,u.fullName,u.phoneNumber,c.dateOfBirth,
                      a.email,'' AS shippingAddress
               FROM Customer c JOIN `User` u ON u.userId=c.userId
               LEFT JOIN Account a ON a.userId=c.userId WHERE c.userId=%s""",
            (customerID,), one=True)

    def findByEmail(self, email):
        return self.db.query(
            """SELECT c.userId AS customerID,u.fullName,u.phoneNumber,c.dateOfBirth,a.email
               FROM Customer c JOIN `User` u ON u.userId=c.userId
               JOIN Account a ON a.userId=c.userId WHERE a.email=%s""",
            (email,), one=True)

    def saveContact(self, customerID, values):
        name = str(values.get('fullName', '')).strip()
        if not 1 <= len(name) <= 150:
            raise DomainError('Invalid customer name')
        with self.db.transaction() as c:
            found = self.db.query('SELECT userId FROM Customer WHERE userId=%s FOR UPDATE',
                                  (customerID,), c, True)
            if not found:
                raise DomainError('Customer not found', 404)
            self.db.query('UPDATE `User` SET fullName=%s,phoneNumber=%s WHERE userId=%s',
                          (name, str(values.get('phoneNumber', ''))[:30], customerID), c)
            if 'dateOfBirth' in values:
                self.db.query('UPDATE Customer SET dateOfBirth=%s WHERE userId=%s',
                              (values['dateOfBirth'], customerID), c)
        return self.findById(customerID)

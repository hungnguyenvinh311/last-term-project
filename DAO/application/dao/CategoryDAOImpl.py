from Model.application.errors import DomainError


class CategoryDAOImpl:
    def __init__(self, db):
        self.db = db

    def findAll(self):
        return self.db.query('SELECT categoryId AS categoryID,groupName,subCategory FROM Category ORDER BY categoryId')

    def update(self, categoryID, values, actorID=None):
        with self.db.transaction() as c:
            row = self.db.query('SELECT * FROM Category WHERE categoryId=%s FOR UPDATE', (categoryID,), c, True)
            if not row:
                raise DomainError('Category not found', 404)
            group = str(values.get('groupName', row['groupName'])).strip()
            sub = str(values.get('subCategory', row['subCategory'])).strip()
            self.db.query('UPDATE Category SET groupName=%s,subCategory=%s WHERE categoryId=%s',
                          (group, sub, categoryID), c)
            self._audit(c, actorID, 'CATEGORY_UPDATED', f'Category:{categoryID}',
                        f"{row['groupName']}|{row['subCategory']}", f'{group}|{sub}')
        return next(r for r in self.findAll() if r['categoryID'] == categoryID)

    def _audit(self, c, actorID, action, target, before, after):
        if actorID is not None:
            self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                          'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)',
                          (actorID, action, target, before, after), c)

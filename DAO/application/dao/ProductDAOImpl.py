import json
import re
from Model.application.errors import DomainError
from Model.application.normalization import matches
from Model.application.entity.Product import Product


class ProductDAOImpl:
    _SELECT = """SELECT p.articleId AS articleID,p.categoryId AS categoryID,p.productName,p.brand,p.price,
                      'VND' AS currency,p.isActive,p.technicalSpecs,p.warrantyTerms,p.imagePath,
                      p.imageEmbedding,p.textEmbedding,c.subCategory,
                      COALESCE(i.onHandQuantity,0) AS onHandQuantity,
                      GREATEST(COALESCE(i.onHandQuantity,0)-COALESCE((SELECT SUM(sc.quantity)
                        FROM StockCommitment sc WHERE sc.inventoryArticleId=p.articleId
                        AND (sc.status='ALLOCATED' OR (sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())))),0),0) AS availableQuantity,
                      mp.operatingSystem,mp.simType,lp.processor,lp.memory,tb.screenSize,tb.stylusSupport,
                      sw.waterResistance,hp.connectionType
               FROM Product p JOIN Category c ON c.categoryId=p.categoryId
               LEFT JOIN Inventory i ON i.articleId=p.articleId
               LEFT JOIN MobilePhone mp ON mp.articleId=p.articleId
               LEFT JOIN Laptop lp ON lp.articleId=p.articleId
               LEFT JOIN Tablet tb ON tb.articleId=p.articleId
               LEFT JOIN SmartWatch sw ON sw.articleId=p.articleId
               LEFT JOIN Headphones hp ON hp.articleId=p.articleId"""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _json_value(value, fallback):
        if value is None or value == '':
            return fallback
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, type(fallback)) else fallback
            except (TypeError, ValueError):
                return fallback
        return fallback

    @classmethod
    def _specs_value(cls, value):
        parsed = cls._json_value(value, {})
        if isinstance(parsed, dict):
            return parsed
        return {'details': value} if value else {}

    def _product(self, row):
        if not row:
            return None
        specs = self._specs_value(row.get('technicalSpecs'))
        row['imageEmbedding'] = self._json_value(row.get('imageEmbedding'), [])
        row['textEmbedding'] = self._json_value(row.get('textEmbedding'), [])
        row['description'] = row.get('description') or specs.get('description') or ''
        subtype = {
            'operatingSystem': row.get('operatingSystem'), 'simType': row.get('simType'),
            'processor': row.get('processor'), 'memory': row.get('memory'),
            'screenSize': row.get('screenSize'), 'stylusSupport': row.get('stylusSupport'),
            'waterResistance': row.get('waterResistance'), 'connectionType': row.get('connectionType')}
        for key, value in subtype.items():
            if value is not None:
                specs.setdefault(key, value)
        row['technicalSpecs'] = specs
        for key in ('operatingSystem','simType','processor','memory','screenSize','stylusSupport',
                    'waterResistance','connectionType'):
            row.pop(key, None)
        row.setdefault('representationUpdateAt', None)
        return Product(**{k: row[k] for k in Product.__dataclass_fields__ if k in row})

    def findById(self, articleID, connection=None):
        row = self.db.query(self._SELECT + ' WHERE p.articleId=%s', (articleID,), connection, True)
        return self._product(row)

    def findActive(self):
        rows = self.db.query(self._SELECT + ' WHERE p.isActive=1 ORDER BY p.articleId')
        return [self._product(row) for row in rows]

    def findByCriteria(self, criteria):
        return [p for p in self.findActive() if matches(p, criteria)]

    def findByRepresentation(self, criteria):
        return self.findByCriteria(criteria)

    def findAlternatives(self, source):
        rows = self.db.query(self._SELECT +
            " WHERE p.categoryId=%s AND p.articleId<>%s AND p.isActive=1 "
            "AND COALESCE(i.onHandQuantity,0)-COALESCE((SELECT SUM(sc.quantity) FROM StockCommitment sc "
            "WHERE sc.inventoryArticleId=p.articleId AND (sc.status='ALLOCATED' OR "
            "(sc.status='HELD' AND (sc.expiresAt IS NULL OR sc.expiresAt>UTC_TIMESTAMP())))),0)>0 "
            'ORDER BY p.articleId',
            (source['categoryID'], source['articleID']))
        return [self._product(row) for row in rows]

    def saveRepresentation(self, articleID, image, text):
        self.db.query('UPDATE Product SET imageEmbedding=%s,textEmbedding=%s WHERE articleId=%s',
                      (json.dumps(image), json.dumps(text), articleID))

    def findAll(self):
        rows = self.db.query(self._SELECT + ' ORDER BY p.articleId')
        return [self._product(row) for row in rows]

    def save(self, values, articleID=None, actorID=None):
        values = dict(values)
        if 'description' in values:
            description = str(values.pop('description') or '').strip()
            specs = self._specs_value(values.get('technicalSpecs'))
            if description:
                specs['description'] = description
            else:
                specs.pop('description', None)
            values['technicalSpecs'] = specs
        allowed = {'categoryID','productName','brand','price','isActive','technicalSpecs',
                   'warrantyTerms','imagePath'}
        values = {key: value for key, value in values.items() if key in allowed}
        if articleID is None:
            required = {'categoryID','productName','brand','price'}
            missing = required - values.keys()
            if missing:
                raise DomainError('Missing product fields: ' + ', '.join(sorted(missing)))
            values.setdefault('isActive', True)
            values.setdefault('technicalSpecs', {})
            values.setdefault('warrantyTerms', 'Bảo hành 12 tháng')
            values.setdefault('imagePath', '')
            with self.db.transaction() as c:
                articleID = self.db.query(
                    """INSERT INTO Product(categoryId,productName,brand,price,isActive,technicalSpecs,
                           warrantyTerms,imagePath,imageEmbedding,textEmbedding)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'[]','[]')""",
                    (values['categoryID'], values['productName'], values['brand'], values['price'],
                     values['isActive'], json.dumps(values['technicalSpecs'], ensure_ascii=False),
                     values['warrantyTerms'], values['imagePath']), c)
                self.db.query('INSERT INTO Inventory(articleId,onHandQuantity) VALUES(%s,0)', (articleID,), c)
                self._sync_subtype(c, articleID, values['categoryID'], values['technicalSpecs'])
                self._audit(c, actorID, 'PRODUCT_CREATED', f'Product:{articleID}', '',
                            json.dumps(values, ensure_ascii=False, default=str))
        else:
            with self.db.transaction() as c:
                old = self.db.query('SELECT * FROM Product WHERE articleId=%s FOR UPDATE', (articleID,), c, True)
                if not old:
                    raise DomainError('Product not found', 404)
                updates = dict(values)
                if 'technicalSpecs' in updates:
                    updates['technicalSpecs'] = json.dumps(updates['technicalSpecs'], ensure_ascii=False)
                if updates:
                    self.db.query('UPDATE Product SET ' + ','.join(f'{k[0].lower()+k[1:]}=%s' for k in updates)
                                  + ' WHERE articleId=%s', (*updates.values(), articleID), c)
                category_id = values.get('categoryID', old['categoryId'])
                specs = values.get('technicalSpecs', self._specs_value(old['technicalSpecs']))
                self._sync_subtype(c, articleID, category_id, specs)
                changed = False
                for key, value in values.items():
                    old_key = {'categoryID':'categoryId'}.get(key, key)
                    old_value = old.get(old_key)
                    if key == 'technicalSpecs':
                        old_value = self._specs_value(old_value)
                    if old_value != value:
                        changed = True
                        break
                if changed:
                    self.db.query("UPDATE Product SET imageEmbedding='[]',textEmbedding='[]' WHERE articleId=%s",
                                  (articleID,), c)
                self._audit(c, actorID, 'PRODUCT_UPDATED', f'Product:{articleID}',
                            json.dumps(old, ensure_ascii=False, default=str),
                            json.dumps(values, ensure_ascii=False, default=str))
        return self.findById(articleID)

    def _sync_subtype(self, connection, articleID, categoryID, specs):
        category = self.db.query('SELECT subCategory FROM Category WHERE categoryId=%s', (categoryID,), connection, True)
        if not category:
            raise DomainError('Category not found', 404)
        kind = re.sub(r'[^a-z]', '', str(category['subCategory']).casefold())
        tables = ('MobilePhone','Laptop','Tablet','SmartWatch','Headphones')
        aliases = {'MobilePhone':('mobilephone','phone','smartphone'), 'Laptop':('laptop','notebook'),
                   'Tablet':('tablet',), 'SmartWatch':('smartwatch','watch'),
                   'Headphones':('headphone','earphone','headset')}
        subtype = next((table for table in tables if any(alias in kind for alias in aliases[table])), None)
        for table in tables:
            if table != subtype:
                self.db.query(f'DELETE FROM {table} WHERE articleId=%s', (articleID,), connection)
        if not subtype:
            return
        fields = {
            'MobilePhone': ('operatingSystem','simType'), 'Laptop': ('processor','memory'),
            'Tablet': ('screenSize','stylusSupport'), 'SmartWatch': ('waterResistance',),
            'Headphones': ('connectionType',)}[subtype]
        defaults = {'operatingSystem':'Not specified','simType':'Not specified','processor':'Not specified',
                    'memory':'Not specified','screenSize':'Not specified','stylusSupport':0,
                    'waterResistance':'Not specified','connectionType':'Not specified'}
        vals = [specs.get(key, defaults[key]) for key in fields]
        self.db.query(f'INSERT INTO {subtype}(articleId,{",".join(fields)}) VALUES(%s,{",".join(["%s"]*len(fields))}) '
                      f'ON DUPLICATE KEY UPDATE {",".join(k+"=VALUES("+k+")" for k in fields)}',
                      (articleID, *vals), connection)

    def _audit(self, c, actorID, action, target, before, after):
        if actorID is not None:
            self.db.query('INSERT INTO AuditLog(employeeId,occurredAt,action,target,beforeValue,afterValue) '
                          'VALUES(%s,UTC_TIMESTAMP(),%s,%s,%s,%s)', (actorID, action, target, before, after), c)

import json
import re
from crawler.config.settings import ROOT, CATEGORIES, database_options

def connect(database=None):
    import mysql.connector
    options=database_options()
    if database is not None:options['database']=database
    return mysql.connector.connect(**options)

def check_connection():
    options=database_options();options.pop('database')
    import mysql.connector
    with mysql.connector.connect(**options) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION(), CURRENT_USER()')
            version,user=cursor.fetchone()
            cursor.execute('SHOW DATABASES')
            databases=[row[0] for row in cursor.fetchall()]
    return dict(server_version=version,authenticated_user=user,databases=databases)

def initialize(database=None):
    """Refuse existing populated/partial schemas rather than silently changing them."""
    import mysql.connector
    options=database_options();configured=options.pop('database');name=database or configured
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',name):raise ValueError('Invalid database name')
    with mysql.connector.connect(**options) as connection:
        cursor=connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s',(name,))
        if cursor.fetchone()[0]:
            raise RuntimeError('Schema already has tables. Do not overwrite: use existing validated schema or choose a new empty database.')
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        cursor.execute(f'USE `{name}`')
        sql=(ROOT/'database/001_catalog.sql').read_text(encoding='utf-8')
        sql='\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
        for statement in sql.split(';'):
            if statement.strip():cursor.execute(statement)
        connection.commit()
    return dict(database=name,status='Created new catalogue schema; no existing tables changed')

def import_products(products,database=None):
    if not products:raise ValueError('No products to import')
    allowed_categories=set(CATEGORIES.values())
    if any(p.get('categoryID') not in allowed_categories for p in products):
        raise ValueError('Product references a category outside the approved catalogue')
    with connect(database) as connection:
        cursor=connection.cursor()
        try:
            connection.start_transaction()
            # Serialize this import so two runs cannot race on IDs or categories.
            cursor.execute("SELECT GET_LOCK('coursework_catalog_import',5)")
            if cursor.fetchone()[0]!=1:raise RuntimeError('Another import is running')
            for name,cid in CATEGORIES.items():
                cursor.execute('SELECT groupName,subCategory FROM Categories WHERE categoryID=%s FOR UPDATE',(cid,))
                existing=cursor.fetchone()
                if existing and existing!=('Electronics',name):raise RuntimeError('Existing category ID belongs to other data')
                cursor.execute('INSERT INTO Categories(categoryID,groupName,subCategory) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE subCategory=VALUES(subCategory)',(cid,'Electronics',name))
            columns=['articleID','categoryID','productName','brand','description','technicalSpecs','warrantyTerms','imagePath','price','currency','isActive']
            # Preserve existing embeddings and representation timestamps on a normal reimport.
            nullable_preserved={'description','technicalSpecs','warrantyTerms'}
            updates=','.join((f'`{x}`=COALESCE(VALUES(`{x}`),`{x}`)' if x in nullable_preserved
                else f'`{x}`=VALUES(`{x}`)') for x in columns[1:] if x!='imagePath')
            updates+=',imagePath=COALESCE(VALUES(imagePath),imagePath)'
            query='INSERT INTO Products('+','.join('`'+x+'`' for x in columns)+') VALUES ('+','.join(['%s']*len(columns))+') ON DUPLICATE KEY UPDATE '+updates
            for p in products:
                cursor.execute('SELECT productName,brand FROM Products WHERE articleID=%s FOR UPDATE',(p['articleID'],))
                existing=cursor.fetchone()
                if existing and existing!=(p['productName'],p['brand']):
                    raise RuntimeError('Product ID conflicts with different existing data; import rolled back')
                values=[json.dumps(p[x],ensure_ascii=False) if x=='technicalSpecs' and p[x] is not None else p[x] for x in columns]
                cursor.execute(query,values)
            connection.commit()
            return dict(imported=len(products),status='committed')
        except Exception:
            connection.rollback();raise
        finally:
            cursor.execute("SELECT RELEASE_LOCK('coursework_catalog_import')")
            cursor.fetchall();cursor.close()

def validate_database(database=None):
    with connect(database) as connection:
        cursor=connection.cursor()
        cursor.execute('SELECT c.subCategory,COUNT(p.articleID) FROM Categories c LEFT JOIN Products p ON c.categoryID=p.categoryID GROUP BY c.categoryID,c.subCategory')
        counts=dict(cursor.fetchall())
        cursor.execute('SELECT COUNT(*) FROM Products p LEFT JOIN Categories c ON c.categoryID=p.categoryID WHERE c.categoryID IS NULL')
        orphans=cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*),COUNT(imagePath),COUNT(imageEmbedding),COUNT(textEmbedding) FROM Products')
        total,images,iv,tv=cursor.fetchone()
    return dict(category_counts=counts,orphan_products=orphans,products=total,main_images=images,image_embeddings=iv,text_embeddings=tv)

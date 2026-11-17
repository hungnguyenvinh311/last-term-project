"""Add application tables, retaining the existing catalogue. No DROP or ALTER."""
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from DAO.application.dao.connection import Database

def migrate(database=None):
    db = Database(database)
    tables = {r['TABLE_NAME'].lower() for r in db.query('SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA=DATABASE()')}
    if not {'products', 'categories'} <= tables:
        raise RuntimeError('Import the retailer catalogue into this database first')
    before = db.query('SELECT COUNT(*) AS count FROM Products', one=True)['count']
    sql = (ROOT/'database/002_application.sql').read_text(encoding='utf-8')
    for match in re.finditer(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\) ENGINE=InnoDB',sql,re.S):
        name,body=match.groups()
        if name.lower() not in tables: continue
        required=set(re.findall(r'(?:^|,)\s*(\w+)\s+(?:INT|VARCHAR|CHAR|ENUM|BOOLEAN|TEXT|DATE|DATETIME|JSON|DECIMAL|DOUBLE)\b',body,re.I))
        columns={r['COLUMN_NAME'] for r in db.query('SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',(name,))}
        if not required<=columns: raise RuntimeError(f'Existing {name} is incompatible; missing {sorted(required-columns)}. No automatic ALTER is performed.')
    with db.transaction() as c:
        for statement in sql.split(';'):
            if statement.strip():
                db.query(statement, connection=c)
        demo_info=(ROOT/'database/003_demo_product_information.sql').read_text(encoding='utf-8')
        for statement in demo_info.split(';'):
            if statement.strip(): db.query(statement,connection=c)
    assert before == db.query('SELECT COUNT(*) AS count FROM Products', one=True)['count']
    print(f'Application schema ready; {before} catalogue products preserved.')

if __name__ == '__main__':
    migrate()

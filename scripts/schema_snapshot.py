"""Read-only, comparable schema evidence; never emits connection credentials."""
import argparse
import json
import re
from pathlib import Path
from DAO.application.dao.connection import Database


def snapshot(db):
    tables = db.query('SHOW TABLES')
    result = {}
    for row in tables:
        table = next(iter(row.values()))
        ddl = db.query('SHOW CREATE TABLE `' + table.replace('`', '``') + '`', one=True)
        result[table] = re.sub(r' AUTO_INCREMENT=\d+', '', ddl['Create Table'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database')
    parser.add_argument('--output', required=True)
    parser.add_argument('--compare')
    args = parser.parse_args()
    result = snapshot(Database(args.database))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.compare:
        assert result == json.loads(Path(args.compare).read_text(encoding='utf-8')), 'Schema changed'
    print(f'{len(result)} tables; schema captured' + ('; unchanged' if args.compare else ''))

from contextlib import contextmanager
import json
import mysql.connector
from Model.application.config.settings import database_options

JSON_COLUMNS = {'technicalSpecs', 'specificationSchema', 'imageEmbedding', 'textEmbedding',
                'specificationSnapshot', 'searchCriteria', 'selectedRegion'}

class Database:
    def __init__(self, database=None):
        self.options = database_options(database)

    @contextmanager
    def transaction(self):
        connection = mysql.connector.connect(**self.options)
        try:
            # DATETIME order defaults follow the application's Vietnam business day.
            # Auth/payment timestamps explicitly using UTC_TIMESTAMP remain UTC.
            connection.time_zone = '+07:00'
            connection.start_transaction()
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def query(self, sql, params=(), connection=None, one=False):
        if connection is None:
            with self.transaction() as connection:
                return self.query(sql, params, connection, one)
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            if not cursor.with_rows:
                return cursor.lastrowid
            rows = cursor.fetchall()
            for row in rows:
                for key in JSON_COLUMNS & row.keys():
                    if isinstance(row[key], (str, bytes)):
                        row[key] = json.loads(row[key])
            return (rows[0] if rows else None) if one else rows
        finally:
            cursor.close()

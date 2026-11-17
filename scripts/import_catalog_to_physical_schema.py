"""Copy the legacy electronics catalogue into the empty physical-model schema.

Dry-run is the default. A database write requires explicit --apply and separate
source/target schema names. This script never drops, clears, or updates a schema.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def _key(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(value).casefold())
    return ''.join(c for c in normalized if c.isalnum())


def _specs(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (bytes, str)):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _stock(specs):
    accepted = {'onhandquantity', 'availablequantity', 'quantity', 'stock', 'stockquantity'}
    for name, value in specs.items():
        key = _key(name)
        if key not in accepted and not any(token in key for token in ('soluong', 'tonkho')):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return value, name
        if isinstance(value, float) and value >= 0 and value.is_integer():
            return int(value), name
        if isinstance(value, str) and re.fullmatch(r'\s*\d+\s*', value):
            return int(value), name
    return None, None


def _subtype(category):
    key = _key(category)
    if any(word in key for word in ('headphone', 'earphone', 'headset')):
        return 'Headphones'
    if any(word in key for word in ('smartphone', 'mobilephone', 'phone')):
        return 'MobilePhone'
    if 'laptop' in key or 'notebook' in key:
        return 'Laptop'
    if 'tablet' in key:
        return 'Tablet'
    if 'smartwatch' in key or key == 'watch':
        return 'SmartWatch'
    return None


def _subtype_values(table, specs):
    aliases = {_key(k): v for k, v in specs.items()}

    def get(name, default):
        value = aliases.get(_key(name), default)
        return 'Not specified' if value is None or str(value).strip() == '' else str(value)[:255]

    if table == 'MobilePhone':
        return (get('operatingSystem', 'Not specified'), get('simType', 'Not specified'))
    if table == 'Laptop':
        return (get('processor', 'Not specified'), get('memory', 'Not specified'))
    if table == 'Tablet':
        stylus = aliases.get('stylussupport', False)
        if isinstance(stylus, str):
            stylus = stylus.casefold() in {'1', 'true', 'yes', 'supported'}
        return (get('screenSize', 'Not specified'), int(bool(stylus)))
    if table == 'SmartWatch':
        return (get('waterResistance', 'Not specified'),)
    return (get('connectionType', 'Not specified'),)


def _database_options(database):
    return dict(host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=database, connection_timeout=10,
                autocommit=False, charset='utf8mb4')


def _tables(connection, database):
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=%s', (database,))
        return {str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()}
    finally:
        cursor.close()


def _rows(connection, table):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM `{table}`")
        return [{str(k).casefold(): v for k, v in row.items()} for row in cursor.fetchall()]
    finally:
        cursor.close()


def inspect_catalog(source_database, target_database):
    if source_database.casefold() == target_database.casefold():
        raise ValueError('Source and target database must be different')
    source = mysql.connector.connect(**_database_options(source_database))
    target = mysql.connector.connect(**_database_options(target_database))
    try:
        source_tables = _tables(source, source_database)
        target_tables = _tables(target, target_database)
        source_category = source_tables.get('categories')
        source_product = source_tables.get('products')
        if not source_category or not source_product:
            raise ValueError('Source must contain Categories and Products tables')
        if not {'category', 'product', 'inventory', 'mobilephone', 'laptop', 'tablet',
                'smartwatch', 'headphones'} <= target_tables.keys():
            raise ValueError('Target does not contain the physical-model commerce tables')

        categories = _rows(source, source_category)
        products = _rows(source, source_product)
        if not categories or not products:
            raise ValueError('Source catalogue is empty; no rows were written')
        category_names = {int(row['categoryid']): str(row['subcategory']) for row in categories}
        missing_stock = []
        invalid = []
        prepared = []
        inventory_table = source_tables.get('inventory') or source_tables.get('inventories')
        inventory_by_product = {}
        if inventory_table:
            try:
                for row in _rows(source, inventory_table):
                    article = row.get('articleid', row.get('inventoryarticleid'))
                    quantity = row.get('onhandquantity', row.get('quantity'))
                    if article is not None and quantity is not None:
                        inventory_by_product[int(article)] = int(quantity)
            except (TypeError, ValueError):
                inventory_by_product = {}

        for row in products:
            article = row.get('articleid')
            category_id = row.get('categoryid')
            try:
                article_id = int(article)
                category_id = int(category_id)
                name = str(row['productname']).strip()
                price = row.get('price')
                if not name or price is None or float(price) < 0:
                    raise ValueError
                currency = str(row.get('currency') or 'VND').upper()
                if currency != 'VND':
                    raise ValueError
                category_name = category_names[category_id]
                subtype = _subtype(category_name)
                if not subtype:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                invalid.append(article)
                continue
            specs = _specs(row.get('technicalspecs'))
            quantity = inventory_by_product.get(article_id)
            stock_key = None
            if quantity is None:
                quantity, stock_key = _stock(specs)
            if quantity is None:
                missing_stock.append(article_id)
                continue
            if stock_key:
                specs.pop(stock_key, None)
            description = row.get('description')
            if description:
                specs['description'] = str(description)
            prepared.append((row, article_id, category_id, subtype, specs, quantity))

        cur = target.cursor()
        try:
            cur.execute('SELECT COUNT(*) FROM Category')
            category_count = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM Product')
            product_count = cur.fetchone()[0]
        finally:
            cur.close()
        return dict(categories=categories, products=prepared, sourceProductCount=len(products),
                    missingStock=missing_stock, invalidProducts=invalid,
                    targetCategoryCount=category_count, targetProductCount=product_count)
    finally:
        source.close()
        target.close()


def import_catalog(source_database, target_database):
    preview = inspect_catalog(source_database, target_database)
    if preview['targetCategoryCount'] or preview['targetProductCount']:
        raise ValueError('Target Category and Product tables must both be empty; no rows were written')
    if preview['invalidProducts'] or preview['missingStock']:
        raise ValueError('Import stopped: resolve invalid products and missing inventory quantities first')

    target = mysql.connector.connect(**_database_options(target_database))
    try:
        cursor = target.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM Category')
            if cursor.fetchone()[0]:
                raise ValueError('Target changed since preview; it is no longer empty')
            cursor.execute('SELECT COUNT(*) FROM Product')
            if cursor.fetchone()[0]:
                raise ValueError('Target changed since preview; it is no longer empty')

            source = mysql.connector.connect(**_database_options(source_database))
            try:
                source_tables = _tables(source, source_database)
                categories = _rows(source, source_tables['categories'])
                products = _rows(source, source_tables['products'])
                inventory_table = source_tables.get('inventory') or source_tables.get('inventories')
                inventory_by_product = {}
                if inventory_table:
                    for row in _rows(source, inventory_table):
                        article = row.get('articleid', row.get('inventoryarticleid'))
                        quantity = row.get('onhandquantity', row.get('quantity'))
                        if article is not None and quantity is not None:
                            inventory_by_product[int(article)] = int(quantity)
            finally:
                source.close()

            for row in categories:
                cursor.execute('INSERT INTO Category(categoryId,groupName,subCategory) VALUES(%s,%s,%s)',
                               (int(row['categoryid']), row['groupname'], row['subcategory']))
            category_names = {int(row['categoryid']): str(row['subcategory']) for row in categories}
            for row in products:
                article_id = int(row['articleid'])
                category_id = int(row['categoryid'])
                specs = _specs(row.get('technicalspecs'))
                quantity = inventory_by_product.get(article_id)
                stock_key = None
                if quantity is None:
                    quantity, stock_key = _stock(specs)
                if stock_key:
                    specs.pop(stock_key, None)
                if row.get('description'):
                    specs['description'] = str(row['description'])
                subtype = _subtype(category_names[category_id])
                image_embedding = _specs_or_array(row.get('imageembedding'))
                text_embedding = _specs_or_array(row.get('textembedding'))
                cursor.execute(
                    """INSERT INTO Product(categoryId,productName,brand,price,isActive,technicalSpecs,
                           warrantyTerms,imagePath,imageEmbedding,textEmbedding,articleId)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (category_id, row['productname'], row.get('brand') or 'Unbranded', row['price'],
                     bool(row.get('isactive', 1)), json.dumps(specs, ensure_ascii=False),
                     row.get('warrantyterms') or 'Bảo hành 12 tháng', row.get('imagepath') or '',
                     json.dumps(image_embedding), json.dumps(text_embedding), article_id))
                cursor.execute('INSERT INTO Inventory(articleId,onHandQuantity) VALUES(%s,%s)',
                               (article_id, quantity))
                fields = {
                    'MobilePhone': ('operatingSystem,simType', _subtype_values(subtype, specs)),
                    'Laptop': ('processor,memory', _subtype_values(subtype, specs)),
                    'Tablet': ('screenSize,stylusSupport', _subtype_values(subtype, specs)),
                    'SmartWatch': ('waterResistance', _subtype_values(subtype, specs)),
                    'Headphones': ('connectionType', _subtype_values(subtype, specs)),
                }
                columns, values = fields[subtype]
                cursor.execute(f'INSERT INTO {subtype}(articleId,{columns}) VALUES(%s,{",".join(["%s"]*len(values))})',
                               (article_id, *values))
            target.commit()
            return len(categories), len(products)
        except Exception:
            target.rollback()
            raise
        finally:
            cursor.close()
    finally:
        target.close()


def _specs_or_array(value):
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, list) else []
        except ValueError:
            return []
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-database', required=True)
    parser.add_argument('--target-database', required=True)
    parser.add_argument('--apply', action='store_true', help='write rows; omitted means preview only')
    args = parser.parse_args()
    for database in (args.source_database, args.target_database):
        if not re.fullmatch(r'[A-Za-z0-9_]{1,64}', database):
            parser.error('Database names may contain only letters, digits, and underscore')
    try:
        preview = inspect_catalog(args.source_database, args.target_database)
        summary = {key: preview[key] for key in ('sourceProductCount', 'missingStock', 'invalidProducts',
                                                  'targetCategoryCount', 'targetProductCount')}
        if not args.apply:
            print(json.dumps({'mode': 'preview', **summary}, ensure_ascii=False, indent=2, default=str))
            return
        categories, products = import_catalog(args.source_database, args.target_database)
        print(json.dumps({'mode': 'imported', 'categories': categories, 'products': products},
                         ensure_ascii=False, indent=2))
    except (ValueError, mysql.connector.Error) as exc:
        raise SystemExit(f'Catalog import stopped: {exc}') from None


if __name__ == '__main__':
    main()

from decimal import Decimal, InvalidOperation
import re
import unicodedata
from crawler.config.settings import CATEGORIES

def clean(value):
    return unicodedata.normalize('NFC',str(value)).strip() if value is not None else None

def category_of(item):
    path=[str(c.get('name') or '').casefold() for c in (item.get('category') or [])]
    leaf=path[-1] if path else ''
    name=str(item.get('name') or '').casefold()
    # Taxonomy, not keyword-only matching: exclude cases/chargers/software.
    if any(x in leaf for x in ['accessor','case','batter','replacement','bands','straps','charg','cable','protector','docks','stands']):return None
    if leaf in {'smartwatches','smart watches','apple watch','apple watch sport'}:return 'Smartwatch'
    if leaf in {'cell phones','all cell phones','unlocked cell phones','all unlocked cell phones','no-contract phones','all no-contract phones','all cell phones with plans','iphone','smartphones'}:
        details=name+' '+str(item.get('description') or '').casefold()
        if not any(x in name for x in ['flip phone','cordless','landline']) and any(x in details for x in ['smartphone','android','iphone','galaxy','xperia','lumia','blackberry']):return 'Smartphone'
    if leaf in {'laptops','all laptops','pc laptops','macbooks','chromebooks','gaming laptops','2-in-1 laptops'}:return 'Laptop'
    if leaf in {'tablets','all tablets','ipads','android tablets','windows tablets'}:return 'Tablet'
    if any(x in leaf for x in ['headphones','earbuds','earbud']) and not any(x in leaf for x in ['accessor','case','amplifier']):return 'Headphones'
    return None

def normalize(item, article_id, category):
    name=clean(item.get('name'))
    if not name:raise ValueError('Missing product name')
    try:price=Decimal(str(item['price']))
    except (KeyError,InvalidOperation,TypeError):raise ValueError('Missing/invalid real source price')
    if not price.is_finite() or price<=0:raise ValueError('Source price must be positive')
    specs={k:clean(item[k]) for k in ['model','upc'] if item.get(k)}
    return dict(articleID=article_id,categoryID=CATEGORIES[category],productName=name,
        brand=clean(item.get('manufacturer')),description=clean(item.get('description')),
        technicalSpecs=specs or None,warrantyTerms=None,imagePath=None,
        price=str(price.quantize(Decimal('0.01'))),currency='USD',isActive=True,
        imageEmbedding=None,textEmbedding=None,representationUpdateAt=None)

def identity(item):
    sku=item.get('sku')
    if sku is None:raise ValueError('Missing source SKU')
    return 'bestbuy_open_data:'+str(sku)

def model_identity(item):
    return (clean(item.get('manufacturer') or '').casefold(),clean(item.get('model') or item.get('name') or '').casefold())

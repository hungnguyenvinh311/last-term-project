from decimal import Decimal
import pytest
from crawler.normalization.products import category_of,normalize,identity
from crawler.validation.catalog import validate

def item(leaf='Laptops',**values):
    return dict(sku=42,name='Real Model',price=123.45,manufacturer='Maker',category=[{'name':leaf}],**values)

def test_no_accessories_are_products():
    p=item('Laptop Cases');assert category_of(p) is None

def test_null_source_fields_do_not_crash_classification():
    assert category_of({'name':None,'category':None}) is None

def test_smartwatch_under_accessory_parent_is_not_a_watch_band():
    p=item('Smartwatches');p['category'].insert(0,{'name':'Cell Phone Accessories'})
    assert category_of(p)=='Smartwatch'
    assert category_of(item('Smartwatch Bands')) is None

def test_exact_source_price_and_missing_fields():
    p=normalize(item(),1,'Laptop')
    assert Decimal(p['price'])==Decimal('123.45')
    assert p['warrantyTerms'] is None and p['imagePath'] is None and p['imageEmbedding'] is None

def test_invalid_prices_rejected():
    for price in [0,-1,float('nan'),float('inf'),'bad']:
        p=item();p['price']=price
        with pytest.raises(ValueError):normalize(p,1,'Laptop')

def test_source_identity_is_independent_of_name():
    assert identity(item())=='bestbuy_open_data:42'

def test_import_rejects_unknown_category_before_connecting(monkeypatch):
    from crawler.database import importer
    def unexpected_connection():
        raise AssertionError('Invalid data must not reach the database')
    monkeypatch.setattr(importer,'connect',unexpected_connection)
    with pytest.raises(ValueError,match='category'):
        importer.import_products([{'categoryID':999}])

def test_validation_detects_duplicate_and_missing_provenance():
    p=normalize(item(),1,'Laptop')
    r=validate([p,p],[])
    assert r['duplicate_ids']==1 and not r['provenance_matches']

def test_repeated_collection_preserves_source_key_mapping(tmp_path,monkeypatch):
    import crawler.cli as cli
    import crawler.sources.bestbuy as source
    import crawler.validation.catalog as validation
    from crawler.storage.files import load_json
    dataset=[item(),dict(item(),sku=99,name='Second Model',model='Model B')]
    monkeypatch.setattr(cli,'ROOT',tmp_path)
    monkeypatch.setattr(validation,'ROOT',tmp_path)
    monkeypatch.setattr(source,'fetch_snapshot',lambda:dataset)
    cli.prepare(20)
    before=load_json(tmp_path/'data/normalized/products.json')
    cli.prepare(20)
    after=load_json(tmp_path/'data/normalized/products.json')
    assert before==after and len(after)==2
    keys=load_json(tmp_path/'data/normalized/product_key_map.json')
    assert len(keys)==2 and len(set(keys.values()))==2

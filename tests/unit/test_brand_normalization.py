import pytest
from Model.application.config.brands import canonical_brand,brand_key
from Model.application.normalization import matches
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.service.SearchService import SearchService
from Model.application.service.ProductService import ProductService
from Model.application.errors import DomainError
from scripts.apply_reviewed_brands import corrected_products

@pytest.mark.parametrize('value,expected',[
    ('Samsung Chính hãng','Samsung'),('samsung chinh hang','Samsung'),
    ('Apple Chính Hãng','Apple'),('  Samsung  ','Samsung'),('Beats','Beats'),
    ('HONOR','HONOR'),(None,None),('A Brand With Spaces','A Brand With Spaces'),
])
def test_brand_suffix_is_not_a_new_brand(value,expected):
    assert canonical_brand(value)==expected
    assert canonical_brand(canonical_brand(value))==expected

def test_search_aliases_work_both_ways_and_conflicts_still_fail():
    p={'articleID':1,'isActive':True,'categoryID':1,'brand':'Samsung Chính hãng','productName':'Phone','price':1}
    assert matches(p,SearchCriteria(brand='Samsung'))
    p['brand']='Samsung'
    assert matches(p,SearchCriteria(brand='Samsung Chính hãng'))
    assert SearchService._filters(SearchCriteria(brand='samsung'),'Samsung Chính hãng').brand=='Samsung'
    with pytest.raises(DomainError):SearchService._filters(SearchCriteria(brand='Samsung'),'Apple Chính hãng')

def test_brand_dropdown_deduplicates_aliases_and_catalogue_filters_them():
    rows=[{'articleID':i,'categoryID':1,'brand':b,'productName':'Phone','imagePath':None} for i,b in enumerate(['Samsung','Samsung Chính hãng','Beats'],1)]
    class Products:
        def findActive(self):return rows
    service=ProductService(Products(),None)
    assert service.getBrands()==['Beats','Samsung']
    assert [p['articleID'] for p in service.filterProducts(brand='Samsung Chính hãng')]==[1,2]
    assert all(p['brand']=='Samsung' for p in service.filterProducts(brand='Samsung'))

def test_approved_beats_correction_is_specific_and_retains_other_fields():
    source=[{'articleID':79,'productName':'Beats Solo Buds','brand':'Apple Chính hãng','price':'100'},
            {'articleID':70,'productName':'Samsung Buds','brand':'Samsung Chính hãng','price':'200'}]
    corrected,changes=corrected_products(source)
    assert corrected[0]['brand']=='Beats' and corrected[1]['brand']=='Samsung'
    assert source[0]['brand']=='Apple Chính hãng'
    assert corrected[0]['price']=='100' and len(changes)==2
    assert corrected_products(corrected)[1]==[]
    source[0]['productName']='Different product'
    with pytest.raises(ValueError):corrected_products(source)

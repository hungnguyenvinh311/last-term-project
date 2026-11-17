import json
import pytest
from crawler.sources.retailers import parse_product

def html(product):
    return '<script type="application/ld+json">'+json.dumps(product)+'</script>'

def test_retailer_price_and_image_are_same_product_without_reviewer_data():
    doc={'@type':'Product','name':'Test-only phone fixture','sku':'unit-test',
         'brand':{'name':'Fixture'},'image':'https://cdn2.cellphones.com.vn/fixture.jpg',
         'offers':{'@type':'Offer','price':'1230000','priceCurrency':'VND'},
         'review':[{'author':{'name':'Do not collect'}}]}
    result=parse_product(html(doc),'https://cellphones.com.vn/fixture.html')
    assert result['price']=='1230000.00' and result['currency']=='VND'
    assert result['image_urls']==[doc['image']]
    assert 'review' not in result and 'author' not in result

def test_category_aggregate_is_not_a_product_price():
    doc={'@type':'Product','name':'Phones','offers':{'@type':'AggregateOffer','lowPrice':1}}
    with pytest.raises(ValueError,match='individual'):
        parse_product(html(doc),'https://cellphones.com.vn/mobile.html')

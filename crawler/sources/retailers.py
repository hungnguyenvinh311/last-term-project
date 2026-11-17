"""Public product pages only: bounded requests, JSON-LD, no reviews/accounts."""
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlparse
import json

SITES={
    'cellphones.com.vn': {'provider':'cellphones','media_hosts':{'cdn2.cellphones.com.vn','cdn.cellphones.com.vn'}},
    'fptshop.com.vn': {'provider':'fptshop','media_hosts':{'cdn2.fptshop.com.vn','images.fpt.shop','cdn.fptshop.com.vn'}},
}

class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.buffer=[];self.documents=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('type')=='application/ld+json':
            self.active=True;self.buffer=[]
    def handle_data(self,data):
        if self.active:self.buffer.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.active:
            try:self.documents.append(json.loads(''.join(self.buffer)))
            except ValueError:pass
            self.active=False

def walk(value):
    if isinstance(value,list):
        for item in value:yield from walk(item)
    elif isinstance(value,dict):
        yield value
        if '@graph' in value:yield from walk(value['@graph'])

def parse_product(html,url):
    host=urlparse(url).hostname
    if host not in SITES:raise ValueError('Unsupported retailer host')
    parser=StructuredData();parser.feed(html)
    for doc in parser.documents:
        for item in walk(doc):
            typ=item.get('@type',[])
            if 'Product' not in (typ if isinstance(typ,list) else [typ]):continue
            offers=item.get('offers',{})
            if isinstance(offers,list):offers=offers[0] if offers else {}
            if offers.get('@type')=='AggregateOffer':continue
            if offers.get('price') is None:continue
            price=Decimal(str(offers['price']))
            if not price.is_finite() or price<=0:continue
            brand=item.get('brand');brand=brand.get('name') if isinstance(brand,dict) else brand
            images=item.get('image',[])
            if isinstance(images,str):images=[images]
            images=[x.get('url') if isinstance(x,dict) else x for x in images]
            images=list(dict.fromkeys(x for x in images if isinstance(x,str) and urlparse(x).hostname in SITES[host]['media_hosts']))
            specs={x['name']:x.get('value') for x in item.get('additionalProperty',[]) if isinstance(x,dict) and x.get('name')}
            # Deliberately exclude review, author and aggregateRating data.
            return dict(provider=SITES[host]['provider'],source_id=str(item.get('sku') or urlparse(url).path),
                source_url=url,productName=item.get('name'),brand=brand,description=item.get('description'),
                technicalSpecs=specs or None,price=str(price.quantize(Decimal('0.01'))),
                currency=offers.get('priceCurrency'),image_urls=images,
                price_basis='Public product-page JSON-LD offer at collection time; promotions may differ',
                rights_status='Retailer-owned content; no open licence asserted',use_scope='Local coursework requested by user')
    raise ValueError('No individual product with a real price found; category aggregate offers are not products')

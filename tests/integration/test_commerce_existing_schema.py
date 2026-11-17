"""Feature-level contracts exercised against an isolated, retained MySQL database."""
import json,os,uuid
from datetime import date
from decimal import Decimal
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from PIL import Image

pytestmark=pytest.mark.skipif(os.getenv('RUN_MYSQL_TESTS')!='1',reason='Requires isolated MySQL integration database')

@pytest.fixture(scope='module')
def commerce(tmp_path_factory):
    from Model.application.config.settings import ROOT
    from crawler.database.importer import initialize,import_products
    from scripts.migrate import migrate
    from scripts.schema_snapshot import snapshot
    from bootstrap import create_app
    from Model.application.ai.IntentExtractorService import IntentExtractorService
    from Model.application.integration.storage.LocalMediaStorage import LocalMediaStorage
    from Model.application.errors import AIUnavailable
    name='ecommerce_test_'+uuid.uuid4().hex[:12]
    initialize(name);import_products(json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8')),name);migrate(name)
    class Offline:
        identity='commerce-offline'
        def encodeText(self,*a): raise AIUnavailable('offline')
        def encodeImage(self,*a): raise AIUnavailable('offline')
    app=create_app(name,{'embedder':Offline(),'intent':IntentExtractorService(),'media':LocalMediaStorage(tmp_path_factory.mktemp('commerce_media'))})
    db=app.state.services['db'];before=snapshot(db)
    (ROOT/'data/test_runs/latest_commerce_test.json').write_text(json.dumps({'database':name,'purpose':'commerce feature tests; retained'}),encoding='utf-8')
    with TestClient(app) as client:
        yield client,app
    assert snapshot(db)==before, 'Tests must not change DDL'

def login(commerce,role='customer'):
    client,app=commerce;service=app.state.services['accounts']
    email=uuid.uuid4().hex+'@example.test';password='commerce-test-123'
    user=service.createStaff(email,password,'Test Staff') if role=='staff' else service.register(email,password,'Test Customer')
    logged=service.login(email,password)
    return {'Authorization':'Bearer '+logged['token']},user

@pytest.fixture(scope='module')
def staff(commerce): return login(commerce,'staff')[0]

@pytest.fixture(scope='module')
def customer(commerce): return login(commerce)

def product(**changes):
    return dict(categoryID=1,productName='Test phone',brand='Test Brand',description='Test description',
                technicalSpecs={'screen':'6 inch'},warrantyTerms='12 months',price='1250000.00',currency='VND',isActive=True,**changes)

def new_product(commerce,staff,**changes):
    body=product();body.update(changes)
    r=commerce[0].post('/api/staff/catalogue/products',headers=staff,json=body)
    assert r.status_code==201,r.text
    return r.json()

def new_order(commerce,staff,method='COD',items=None):
    client,app=commerce;headers,user=login(commerce)
    items=items or [(new_product(commerce,staff),2)]
    for p,qty in items:
        assert client.post('/api/cart/items',headers=headers,json={'articleID':p['articleID'],'quantity':qty}).status_code==200
    payload=dict(paymentMethod=method,shippingAddress='Original order street 123',recipientPhone='0901234567',
                 prices={str(p['articleID']):p['price'] for p,q in items})
    r=client.post('/api/orders',headers=headers,json=payload);assert r.status_code==201,r.text
    return r.json(),headers,user

@pytest.mark.parametrize('path,method,body',[
    ('/staff/catalogue/products','get',None),
    ('/staff/catalogue/categories','get',None),
    ('/staff/catalogue/products','post',product()),
    ('/staff/accounts','post',{'email':'x@example.test','password':'test-password-123','fullName':'X'}),
    ('/staff/orders/1','get',None),
    ('/staff/orders/1/cancel','post',{}),
    ('/staff/orders/1/cod-confirmation','post',{'amount':1,'trackingNumber':'x','reference':'ABC'}),
    ('/staff/accounts/1/customer-history','get',None),
    ('/staff/reports/sales?start=2026-01-01&end=2026-01-02','get',None),
])
def test_staff_routes_reject_guest_and_customer(commerce,customer,path,method,body):
    client,app=commerce
    assert client.request(method,'/api'+path,json=body).status_code==401
    assert client.request(method,'/api'+path,json=body,headers=customer[0]).status_code==403

def test_staff_creation_and_lock_revoke_sessions(commerce,staff):
    client,app=commerce;h,u=login(commerce)
    created=client.post('/api/staff/accounts',headers=staff,json={'email':uuid.uuid4().hex+'@example.test','password':'test-password-123','fullName':'New Staff'})
    assert created.status_code==201 and created.json()['role']=='staff'
    accounts=client.get('/api/staff/accounts',headers=staff).json()
    assert all('passwordHash' not in a for a in accounts)
    assert client.put('/api/staff/accounts/'+str(u['accountID']),headers=staff,json={'active':False}).status_code==200
    assert client.get('/api/accounts/me',headers=h).status_code==401
    assert client.put('/api/staff/accounts/'+str(u['accountID']),headers=staff,json={'active':True}).status_code==200
    assert client.get('/api/accounts/me',headers=h).status_code==401  # unlocking does not resurrect sessions

def test_registration_cannot_choose_staff_role(commerce):
    client,_=commerce
    r=client.post('/api/accounts/register',json={'email':uuid.uuid4().hex+'@example.test','password':'test-password-123','fullName':'Customer','role':'staff'})
    assert r.status_code==201 and r.json()['role']=='customer'

@pytest.mark.parametrize('change',[
    {'price':'-1'},{'price':'NaN'},{'price':'10000000000000000.00'},{'categoryID':6},
    {'productName':'   '},{'currency':'USD'},{'technicalSpecs':{'a':{'nested':True}}},
    {'imagePath':'C:/private.txt'},{'imageEmbedding':[1,0]},
])
def test_catalogue_rejects_invalid_or_client_internal_fields(commerce,staff,change):
    body=product();body.update(change)
    assert commerce[0].post('/api/staff/catalogue/products',headers=staff,json=body).status_code==422

def test_catalogue_edit_clears_stale_vectors_but_price_does_not(commerce,staff):
    client,app=commerce;db=app.state.services['db'];p=new_product(commerce,staff);pid=p['articleID']
    db.query("UPDATE Products SET imageEmbedding='[1,0]',textEmbedding='[1,0]',representationUpdateAt=UTC_TIMESTAMP() WHERE articleID=%s",(pid,))
    body=product();body['price']='1400000'
    r=client.put(f'/api/staff/catalogue/products/{pid}',headers=staff,json=body)
    assert r.status_code==200
    assert db.query('SELECT imageEmbedding FROM Products WHERE articleID=%s',(pid,),one=True)['imageEmbedding']==[1,0]
    body['productName']='Updated phone'
    assert client.put(f'/api/staff/catalogue/products/{pid}',headers=staff,json=body).status_code==200
    row=db.query('SELECT * FROM Products WHERE articleID=%s',(pid,),one=True)
    assert row['imageEmbedding'] is None and row['textEmbedding'] is None and row['representationUpdateAt'] is None
    assert 'imagePath' not in r.json() and 'imageEmbedding' not in r.json()

def test_concurrent_product_ids_are_distinct_without_altering_schema(commerce,staff):
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(lambda i:new_product(commerce,staff,productName='Concurrent '+str(i)),range(4)))
    assert len({r['articleID'] for r in rows})==4

def test_product_image_validation_storage_and_archive(commerce,staff):
    client,app=commerce;p=new_product(commerce,staff);path=f"/api/staff/catalogue/products/{p['articleID']}"
    assert client.post(path+'/image',headers=staff,files={'file':('x.jpg',b'invalid','image/jpeg')}).status_code==400
    buf=BytesIO();Image.new('RGB',(32,32),'orange').save(buf,'PNG')
    r=client.post(path+'/image',headers=staff,files={'file':('../../escape.png',buf.getvalue(),'image/png')})
    assert r.status_code==200,r.text
    assert client.get(r.json()['imageUrl']).status_code==200
    assert client.delete(path,headers=staff).status_code==200
    assert client.get('/api/products/'+str(p['articleID'])).status_code==404
    assert app.state.services['products'].findById(p['articleID'])['isActive']==0

def test_categories_update_metadata_without_changing_ai_taxonomy(commerce,staff):
    client,_=commerce;old=client.get('/api/staff/catalogue/categories',headers=staff).json()
    r=client.put('/api/staff/catalogue/categories/1',headers=staff,json={'groupName':'Electronics','specificationSchema':{'screen':'string'}})
    assert r.status_code==200 and r.json()['subCategory']==old[0]['subCategory']
    assert client.put('/api/staff/catalogue/categories/1',headers=staff,json={'groupName':'X','subCategory':'Watch'}).status_code==422
    assert client.put('/api/staff/catalogue/categories/99',headers=staff,json={'groupName':'X'}).status_code==404
    assert len(client.get('/api/staff/catalogue/categories',headers=staff).json())==5

def test_server_pricing_fee_and_immutable_order_snapshots(commerce,staff,monkeypatch):
    client,app=commerce;monkeypatch.setenv('APP_DEMO_SHIPPING_FEE','30000')
    p=new_product(commerce,staff);h,user=login(commerce)
    assert client.post('/api/cart/items',headers=h,json={'articleID':p['articleID'],'quantity':2}).status_code==200
    quote=client.get('/api/cart',headers=h).json()['pricing']
    assert Decimal(str(quote['totalAmount']))==Decimal('2530000')
    payload=dict(paymentMethod='ONLINE',shippingAddress='Snapshot street 123',recipientPhone='0901234567',prices={str(p['articleID']):p['price']},totalAmount=1,shippingFee=0,discountAmount=999999)
    r=client.post('/api/orders',headers=h,json=payload);assert r.status_code==201,r.text
    o=r.json();assert Decimal(str(o['totalAmount']))==Decimal('2530000') and Decimal(str(o['discountAmount']))==0
    before=client.get('/api/orders/'+str(o['orderID']),headers=h).json()
    assert Decimal(str(before['payment']['amount']))==Decimal('2530000')
    body=product();body.update(productName='Changed name',price='1',warrantyTerms='Changed warranty')
    assert client.put('/api/staff/catalogue/products/'+str(p['articleID']),headers=staff,json=body).status_code==200
    assert client.put('/api/accounts/me',headers=h,json={'fullName':'New Customer','shippingAddress':'New address 456','phoneNumber':'0901234567','dateOfBirth':'2000-01-01'}).status_code==200
    after=client.get('/api/orders/'+str(o['orderID']),headers=h).json()
    assert after['items']==before['items'] and after['shippingAddress']==before['shippingAddress']
    assert after['totalAmount']==before['totalAmount']

def test_staff_detail_cancel_and_snapshot_for_archived_product(commerce,staff):
    client,_=commerce;p=new_product(commerce,staff);o,h,user=new_order(commerce,staff,items=[(p,1)])
    oid=o['orderID']
    client.delete('/api/staff/catalogue/products/'+str(p['articleID']),headers=staff)
    detail=client.get('/api/staff/orders/'+str(oid),headers=staff)
    assert detail.status_code==200 and detail.json()['customer']['customerID']==user['customerID']
    assert detail.json()['items'][0]['productNameSnapshot']==p['productName']
    assert 'passwordHash' not in str(detail.json())
    r=client.post(f'/api/staff/orders/{oid}/cancel',headers=staff)
    assert r.status_code==200 and r.json()['status']=='Cancelled'
    assert client.post(f'/api/staff/orders/{oid}/cancel',headers=staff).status_code==200
    assert client.post('/api/cart/items',headers=h,json={'articleID':p['articleID'],'quantity':1}).status_code==404

def advance(client,staff,oid,customer):
    for status in ['Packing','Packed','Dispatched']:
        r=client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':status})
        assert r.status_code==200,r.text
    assert client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':'Delivered'}).status_code==422
    assert client.post(f'/api/orders/{oid}/confirm-delivery',headers=customer).status_code==200

def test_fulfilment_strict_sequence_idempotence_and_cancellation_boundary(commerce,staff):
    client,app=commerce;o,h,user=new_order(commerce,staff);oid=o['orderID']
    assert client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':'Dispatched'}).status_code==409
    for status in ['Packing','Packed','Dispatched']:
        r=client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':status})
        assert r.status_code==200
        before=client.get(f'/api/staff/orders/{oid}',headers=staff).json()
        assert client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':status}).status_code==200
        after=client.get(f'/api/staff/orders/{oid}',headers=staff).json()
        assert after['version']==before['version'] and after['shipment']==before['shipment']
        assert client.post(f'/api/staff/orders/{oid}/cancel',headers=staff).status_code==409
    assert client.post(f'/api/orders/{oid}/confirm-delivery',headers=staff).status_code==403
    assert client.post(f'/api/orders/{oid}/confirm-delivery',headers=h).status_code==200
    after=client.get(f'/api/staff/orders/{oid}',headers=staff).json()
    assert after['shipment']['deliveredAt']
    assert client.put(f'/api/staff/orders/{oid}/shipment',headers=staff,json={'status':'Packing'}).status_code==409
    online,_,_=new_order(commerce,staff,method='ONLINE')
    assert client.put(f"/api/staff/orders/{online['orderID']}/shipment",headers=staff,json={'status':'Packing'}).status_code==409

def test_cod_confirmation_validates_delivery_amount_reference_and_is_idempotent(commerce,staff):
    client,_=commerce;o,h,user=new_order(commerce,staff);oid=o['orderID'];url=f'/api/staff/orders/{oid}/cod-confirmation'
    payload={'amount':o['totalAmount'],'trackingNumber':'DEMO-SHIP-'+str(oid),'reference':'COD-'+str(oid)}
    assert client.post(url,headers=staff,json=payload).status_code==409
    advance(client,staff,oid,h)
    for change in [{'amount':1},{'trackingNumber':'wrong'}]:
        assert client.post(url,headers=staff,json={**payload,**change}).status_code==409
    r=client.post(url,headers=staff,json=payload);assert r.status_code==200 and r.json()['status']=='Paid' and r.json()['paidAt']
    assert client.post(url,headers=staff,json=payload).json()==r.json()
    assert client.post(url,headers=staff,json={**payload,'reference':'OTHER'}).status_code==409
    other,other_h,_=new_order(commerce,staff);advance(client,staff,other['orderID'],other_h)
    assert client.post(f"/api/staff/orders/{other['orderID']}/cod-confirmation",headers=staff,json={**payload,'trackingNumber':'DEMO-SHIP-'+str(other['orderID'])}).status_code==409

def test_online_paid_cancel_stays_refund_required(commerce,staff):
    client,_=commerce;o,h,_=new_order(commerce,staff,method='ONLINE');oid=o['orderID']
    assert client.post(f'/api/orders/{oid}/payment',headers=h,json={'scenario':'success'}).status_code==404
    assert client.post(f'/api/staff/orders/{oid}/online-payment',headers=h,json={'scenario':'success'}).status_code==403
    assert client.post(f'/api/staff/orders/{oid}/online-payment',headers=staff,json={'scenario':'success'}).status_code==200
    r=client.post(f'/api/staff/orders/{oid}/cancel',headers=staff)
    assert r.status_code==200 and r.json()['payment']['status']=='RefundRequired'

def test_staff_customer_history_shows_orders_and_only_paid_delivered_total(commerce,staff):
    client,_=commerce
    delivered,customer,user=new_order(commerce,staff,method='ONLINE')
    unpaid,_,_=new_order(commerce,staff,method='ONLINE')
    oid=delivered['orderID']
    assert client.post(f'/api/staff/orders/{oid}/online-payment',headers=staff,json={'scenario':'success'}).status_code==200
    advance(client,staff,oid,customer)
    assert client.post(f"/api/staff/orders/{unpaid['orderID']}/online-payment",headers=staff,json={'scenario':'pending'}).status_code==200
    url=f"/api/staff/accounts/{user['accountID']}/customer-history"
    assert client.get(url,headers=customer).status_code==403
    response=client.get(url,headers=staff)
    assert response.status_code==200,response.text
    history=response.json()
    assert history['customer']['customerID']==user['customerID']
    assert {row['orderID'] for row in history['orders']} >= {oid,unpaid['orderID']}
    assert Decimal(str(history['totalPaidDelivered']))==Decimal(str(delivered['totalAmount']))

def test_concurrent_cod_confirmation_is_one_stable_summary(commerce,staff):
    client,app=commerce;o,h,_=new_order(commerce,staff);oid=o['orderID'];advance(client,staff,oid,h)
    payload={'amount':o['totalAmount'],'trackingNumber':'DEMO-SHIP-'+str(oid),'reference':'RACE-COD-'+str(oid)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.post(f'/api/staff/orders/{oid}/cod-confirmation',headers=staff,json=payload),range(4)))
    assert all(r.status_code==200 for r in responses)
    assert all(r.json()==responses[0].json() for r in responses)
    assert app.state.services['db'].query('SELECT COUNT(*) AS n FROM Payments WHERE orderID=%s',(oid,),one=True)['n']==1

def test_checkout_price_change_rejects_old_quote_without_emptying_cart(commerce,staff):
    client,_=commerce;p=new_product(commerce,staff);h,user=login(commerce)
    client.post('/api/cart/items',headers=h,json={'articleID':p['articleID'],'quantity':2})
    body=product();body['price']='2000000'
    assert client.put('/api/staff/catalogue/products/'+str(p['articleID']),headers=staff,json=body).status_code==200
    payload=dict(paymentMethod='COD',shippingAddress='Street address 123',recipientPhone='0901234567',prices={str(p['articleID']):p['price']})
    assert client.post('/api/orders',headers=h,json=payload).status_code==409
    assert client.get('/api/cart',headers=h).json()['items'][0]['quantity']==2
    assert client.get('/api/orders',headers=h).json()==[]

@pytest.mark.parametrize('change',[
    {'dateOfBirth':'2999-01-01'},{'dateOfBirth':'1899-01-01'},{'dateOfBirth':'not-date'},
    {'phoneNumber':'abcdefghij'},{'fullName':'   '},
])
def test_profile_rejects_bad_data(commerce,customer,change):
    body={'fullName':'Customer','phoneNumber':'0901234567','shippingAddress':'Address'};body.update(change)
    assert commerce[0].put('/api/accounts/me',headers=customer[0],json=body).status_code in (400,422)

def test_profile_dob_preserved_when_omitted_and_can_be_cleared(commerce,customer):
    client,_=commerce;h=customer[0]
    base={'fullName':'Customer','phoneNumber':'0901234567','shippingAddress':'Address'}
    assert client.put('/api/accounts/me',headers=h,json={**base,'dateOfBirth':'2000-01-02'}).json()['dateOfBirth']=='2000-01-02'
    assert client.put('/api/accounts/me',headers=h,json=base).json()['dateOfBirth']=='2000-01-02'
    assert client.put('/api/accounts/me',headers=h,json={**base,'dateOfBirth':None}).json()['dateOfBirth'] is None

def test_report_no_duplicate_order_totals_filters_exports_and_exclusions(commerce,staff):
    client,app=commerce;p=new_product(commerce,staff,price='100',brand='Report A');q=new_product(commerce,staff,price='200',brand='Report B',categoryID=3)
    o,h,_=new_order(commerce,staff,items=[(p,2),(q,1)])
    # Use a distinct date to isolate exact expected aggregates from other fixtures.
    app.state.services['db'].query("UPDATE Orders SET createdAt='2025-06-15 12:00:00' WHERE orderID=%s",(o['orderID'],))
    base='/api/staff/reports/sales?start=2025-06-15&end=2025-06-15'
    r=client.get(base,headers=staff);assert r.status_code==200,r.text
    report=r.json();assert report['orderCount']==1 and report['units']==3
    assert Decimal(str(report['itemGrossSales']))==400 and Decimal(str(report['matchedOrdersNetMerchandise']))==400
    filtered=client.get(base+'&categoryID=3',headers=staff).json()
    assert filtered['units']==1 and Decimal(str(filtered['itemGrossSales']))==200 and Decimal(str(filtered['matchedOrdersNetMerchandise']))==400
    assert client.get(base+'&brand=Report%20A',headers=staff).json()['units']==2
    assert client.get(base+'&paymentMethod=ONLINE',headers=staff).json()['orderCount']==0
    csv=client.get(base+'&format=csv',headers=staff)
    assert csv.status_code==200 and csv.content.startswith(b'\xef\xbb\xbf') and 'grossSales' in csv.text
    pdf=client.get(base+'&format=pdf',headers=staff)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-') and b'%%EOF' in pdf.content
    assert client.get('/api/staff/reports/sales?start=2025-06-16&end=2025-06-15',headers=staff).status_code==400
    assert client.post(f"/api/staff/orders/{o['orderID']}/cancel",headers=staff).status_code==200
    cancelled=client.get(base,headers=staff).json()
    assert cancelled['orderCount']==1 and cancelled['units']==0 and Decimal(str(cancelled['itemGrossSales']))==0

def test_comparison_same_category_and_warranty_exposed(commerce,staff):
    client,_=commerce;p=new_product(commerce,staff);q=new_product(commerce,staff,warrantyTerms='24 months')
    r=client.post('/api/products/compare',json={'ids':[p['articleID'],q['articleID']]})
    assert r.status_code==200,r.text
    assert {x['warrantyTerms'] for x in r.json()}=={'12 months','24 months'}

def test_report_business_day_matches_order_timestamp_timezone(commerce,staff):
    client,app=commerce;p=new_product(commerce,staff);order,_,_=new_order(commerce,staff,items=[(p,1)])
    clock=app.state.services['db'].query('SELECT NOW() AS businessNow,@@session.time_zone AS zone',one=True)
    assert clock['zone']=='+07:00'
    day=clock['businessNow'].date().isoformat()
    r=client.get(f'/api/staff/reports/sales?start={day}&end={day}',headers=staff)
    assert r.status_code==200 and r.json()['timezone']=='Asia/Ho_Chi_Minh (UTC+07:00)'
    assert p['articleID'] in [i['articleID'] for i in r.json()['topProducts']]

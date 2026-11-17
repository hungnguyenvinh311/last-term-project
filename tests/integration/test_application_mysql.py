"""Opt-in real MySQL tests. A new named test DB is retained; no user database is deleted."""
import os,json,uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from Model.application.errors import AIUnavailable

pytestmark=pytest.mark.skipif(os.getenv('RUN_MYSQL_TESTS')!='1',reason='Set RUN_MYSQL_TESTS=1 to create an isolated MySQL test database')

@pytest.fixture(scope='module')
def app_client():
    from Model.application.config.settings import ROOT,database_options
    from crawler.database.importer import initialize,import_products
    from scripts.migrate import migrate
    from bootstrap import create_app
    from crawler.storage.files import save_json
    name='ecommerce_test_'+uuid.uuid4().hex[:12]
    initialize(name)
    records=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    import_products(records,name);migrate(name)
    class OfflineEncoder:
        identity='test-unavailable-encoder'
        def encodeText(self,*a): raise AIUnavailable('offline test')
        def encodeImage(self,*a): raise AIUnavailable('offline test')
    from Model.application.ai.IntentExtractorService import IntentExtractorService
    app=create_app(name,{'embedder':OfflineEncoder(),'intent':IntentExtractorService()})
    save_json(ROOT/'data/test_runs/latest_mysql_test.json',{'database':name,'purpose':'isolated integration fixtures; retained without deleting user data'})
    with TestClient(app) as client: yield client,app

def account(client):
    email='test-'+uuid.uuid4().hex[:8]+'@example.test'
    r=client.post('/api/accounts/register',json={'email':email,'password':'test-password-123','fullName':'Integration Test'})
    assert r.status_code==201,r.text
    r=client.post('/api/accounts/login',json={'email':email,'password':'test-password-123'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']},r.json()['account']

def test_catalogue_and_registration(app_client):
    client,app=app_client
    assert client.get('/api/health').status_code==200
    rows=client.get('/api/products').json();assert len(rows)==100
    assert 'imageEmbedding' not in rows[0] and 'imagePath' not in rows[0]
    assert client.get(rows[0]['imageUrl']).status_code==200
    headers,a=account(client)
    assert client.get('/api/accounts/me',headers=headers).json()['account']['role']=='customer'
    assert client.get('/api/staff/accounts',headers=headers).status_code==403
    assert client.get('/api/cart').status_code==401
    assert client.post('/api/accounts/register',json={'email':a['email'],'password':'test-password-123','fullName':'Duplicate','role':'staff'}).status_code==409
    assert client.post('/api/accounts/logout',headers=headers).status_code==200
    assert client.get('/api/accounts/me',headers=headers).status_code==401

def test_text_voice_history_and_recommendation(app_client):
    client,app=app_client;headers,a=account(client)
    headers['X-Search-Context']=uuid.uuid4().hex
    response=client.post('/api/search/text',headers=headers,json={'text':'điện thoại Samsung dưới 40 triệu','reset':True})
    assert response.status_code==200,response.text
    result=response.json();assert result['fallback'] is True and len(result['products'])>0
    assert all(p['categoryID']==1 and float(p['price'])<=40_000_000 and p['brand'].lower()=='samsung' for p in result['products'])
    qid=result['queryID'];db=app.state.services['db']
    assert db.query('SELECT * FROM textQueries WHERE queryID=%s',(qid,),one=True)
    voice=client.post('/api/search/text',headers=headers,json={'text':'điện thoại','queryType':'voice','reset':True})
    assert voice.status_code==200
    qid=voice.json()['queryID']
    assert db.query('SELECT * FROM voiceQueries WHERE queryID=%s',(qid,),one=True)
    assert not db.query('SELECT * FROM textQueries WHERE queryID=%s',(qid,),one=True)
    count=db.query('SELECT COUNT(*) AS n FROM searchQueries',one=True)['n']
    source=result['products'][0]['articleID'];rec=client.get(f'/api/products/{source}/recommendations').json()
    assert len(rec['products'])==8 and rec['fallback'] is True
    assert all(p['categoryID']==1 and p['articleID']!=source and p['fallback'] for p in rec['products'])
    assert db.query('SELECT COUNT(*) AS n FROM searchQueries',one=True)['n']==count
    assert client.post('/api/search/image',files={'file':('fake.jpg',b'not-an-image','image/jpeg')}).status_code==400
    # Parent/results rollback when an invalid product reference is rejected by MySQL.
    from DAO.application.dao.SearchQueryDAOImpl import SearchQueryDAOImpl
    import mysql.connector
    with pytest.raises(mysql.connector.IntegrityError) as error:
        SearchQueryDAOImpl(db).saveWithResults(a['customerID'],'text',{}, {'text':'rollback'},[{'articleID':99999999,'score':1}])
    assert error.value.errno==1452
    assert db.query('SELECT COUNT(*) AS n FROM searchQueries',one=True)['n']==count

def test_cart_checkout_payment_ownership_and_shipments(app_client):
    client,app=app_client;headers,a=account(client);other,b=account(client)
    p=client.get('/api/products').json()[0];id=p['articleID']
    assert client.post('/api/cart/items',headers=headers,json={'articleID':id,'quantity':2}).status_code==200
    assert client.post('/api/cart/items',headers=headers,json={'articleID':id,'quantity':1}).json()['items'][0]['quantity']==3
    assert client.get('/api/cart',headers=other).json()['items']==[]
    payload={'paymentMethod':'ONLINE','shippingAddress':'Demo street 123','recipientPhone':'0901234567','prices':{str(id):0}}
    assert client.post('/api/orders',headers=headers,json=payload).status_code==409
    payload['prices'][str(id)]=p['price']
    r=client.post('/api/orders',headers=headers,json=payload);assert r.status_code==201,r.text
    order=r.json();oid=order['orderID']
    assert len(order['items'])==1 and order['items'][0]['quantity']==3
    assert client.get(f'/api/orders/{oid}',headers=other).status_code==404
    assert client.post('/api/orders',headers=headers,json=payload).status_code==409
    assert client.post(f'/api/orders/{oid}/payment',headers=headers,json={'scenario':'success'}).status_code==404
    assert client.put(f'/api/staff/orders/{oid}/shipment',headers=headers,json={'status':'Packing'}).status_code==403
    from Model.application.service.AccountService import hash_password
    service=app.state.services['accounts']
    staff=service.accounts.register('staff-'+uuid.uuid4().hex[:8]+'@example.test',hash_password('test-password-123'),'Test Staff','staff')
    logged=service.login(staff['email'],'test-password-123');sh={'Authorization':'Bearer '+logged['token']}
    paid=client.post(f'/api/staff/orders/{oid}/online-payment',headers=sh,json={'scenario':'success'})
    assert paid.status_code==200 and paid.json()['status']=='Paid'
    assert client.post(f'/api/staff/orders/{oid}/online-payment',headers=sh,json={'scenario':'failure'}).json()['status']=='Paid'
    for status in ['Packing','Packed','Dispatched']:
        response=client.put(f'/api/staff/orders/{oid}/shipment',headers=sh,json={'status':status});assert response.status_code==200,response.text
    assert client.put(f'/api/staff/orders/{oid}/shipment',headers=sh,json={'status':'Delivered'}).status_code==422
    assert client.post(f'/api/orders/{oid}/confirm-delivery',headers=other).status_code==404
    assert client.post(f'/api/orders/{oid}/confirm-delivery',headers=headers).status_code==200
    assert client.post(f'/api/orders/{oid}/cancel',headers=headers).status_code==409
    assert client.get(f'/api/orders/{oid}',headers=headers).json()['shipment']['status']=='Delivered'
    assert client.put(f'/api/staff/accounts/{a["accountID"]}',headers=sh,json={'active':False}).status_code==200
    assert client.get('/api/accounts/me',headers=headers).status_code==401

def test_cod_pending_cancellation_and_profile(app_client):
    client,app=app_client;headers,a=account(client)
    p=client.get('/api/products').json()[0]
    payload={'paymentMethod':'COD','shippingAddress':'Demo street 123','recipientPhone':'0901234567','prices':{str(p['articleID']):p['price']}}
    assert client.put('/api/accounts/me',headers=headers,json={'fullName':'Updated Profile','phoneNumber':'0901234567','shippingAddress':'Demo street 123'}).json()['fullName']=='Updated Profile'
    def create(method):
        assert client.post('/api/cart/items',headers=headers,json={'articleID':p['articleID'],'quantity':1}).status_code==200
        r=client.post('/api/orders',headers=headers,json={**payload,'paymentMethod':method});assert r.status_code==201,r.text
        return r.json()['orderID']
    cod=create('COD')
    assert client.get(f'/api/orders/{cod}',headers=headers).json()['payment']['status']=='UnpaidCOD'
    assert client.post(f'/api/orders/{cod}/payment',headers=headers,json={'scenario':'success'}).status_code==404
    from Model.application.service.AccountService import hash_password
    service=app.state.services['accounts']
    staff=service.accounts.register('review-'+uuid.uuid4().hex[:8]+'@example.test',hash_password('test-password-123'),'Review Staff','staff')
    token=service.login(staff['email'],'test-password-123')['token'];sh={'Authorization':'Bearer '+token}
    assert client.post(f'/api/staff/orders/{cod}/online-payment',headers=sh,json={'scenario':'success'}).status_code==409
    assert client.post(f'/api/orders/{cod}/cancel',headers=headers).json()['status']=='Cancelled'
    pending=create('ONLINE')
    assert client.post(f'/api/staff/orders/{pending}/online-payment',headers=sh,json={'scenario':'pending'}).json()['status']=='Pending'
    assert client.post(f'/api/orders/{pending}/cancel',headers=headers).json()['payment']['status']=='PendingReview'
    reconciled=create('ONLINE')
    assert client.post(f'/api/staff/orders/{reconciled}/online-payment',headers=sh,json={'scenario':'pending'}).json()['status']=='Pending'
    assert client.post(f'/api/staff/orders/{reconciled}/online-payment',headers=sh,json={'scenario':'success'}).status_code==200
    assert client.get(f'/api/orders/{reconciled}',headers=headers).json()['payment']['status']=='Paid'
    paid=create('ONLINE')
    assert client.post(f'/api/staff/orders/{paid}/online-payment',headers=sh,json={'scenario':'success'}).status_code==200
    assert client.post(f'/api/orders/{paid}/cancel',headers=headers).json()['payment']['status']=='RefundRequired'

def test_brand_filter_catalogue_and_search_can_be_changed_or_cleared(app_client):
    client,app=app_client
    brands=client.get('/api/products/brands')
    assert brands.status_code==200 and 'Samsung' in brands.json() and 'Apple' in brands.json()
    rows=client.get('/api/products',params={'brand':'Samsung','category':1}).json()
    assert rows and all(p['brand']=='Samsung' and p['categoryID']==1 for p in rows)
    headers={'X-Search-Context':uuid.uuid4().hex}
    for brand in ['Samsung','Apple',None]:
        r=client.post('/api/search/text',headers=headers,json={'text':'điện thoại','brand':brand,'categoryID':1})
        assert r.status_code==200,r.text
        assert r.json()['products']
        if brand:assert all(p['brand']==brand for p in r.json()['products'])
        else:assert len({p['brand'] for p in r.json()['products']})>1
    conflict=client.post('/api/search/text',headers=headers,json={'text':'điện thoại Samsung','brand':'Apple','reset':True})
    assert conflict.status_code==400

def test_promotional_brand_alias_is_equivalent_through_http_and_history(app_client):
    client,app=app_client;db=app.state.services['db']
    p=next(p for p in client.get('/api/products').json() if p['brand']=='Samsung')
    try:
        db.query('UPDATE Products SET brand=%s WHERE articleID=%s',('Samsung Chính hãng',p['articleID']))
        for alias in ['Samsung','Samsung Chính hãng']:
            rows=client.get('/api/products',params={'brand':alias}).json()
            assert p['articleID'] in [r['articleID'] for r in rows]
            assert all(r['brand']=='Samsung' for r in rows)
            r=client.post('/api/search/text',headers={'X-Search-Context':uuid.uuid4().hex},
                          json={'text':'điện thoại Samsung','brand':alias,'reset':True})
            assert r.status_code==200,r.text
            assert r.json()['products'] and r.json()['criteria']['brand']=='Samsung'
            assert all(row['brand']=='Samsung' for row in r.json()['products'])
        brands=client.get('/api/products/brands').json()
        assert 'Samsung' in brands and 'Samsung Chính hãng' not in brands
    finally:
        db.query('UPDATE Products SET brand=%s WHERE articleID=%s',(p['brand'],p['articleID']))

def test_corrected_beats_product_is_not_apple(app_client):
    client,app=app_client
    assert client.get('/api/products/79').json()['brand']=='Beats'
    rows=client.get('/api/products',params={'brand':'Beats'}).json()
    assert 79 in [p['articleID'] for p in rows]
    assert 79 not in [p['articleID'] for p in client.get('/api/products',params={'brand':'Apple Chính hãng'}).json()]
    response=client.post('/api/search/text',headers={'X-Search-Context':uuid.uuid4().hex},json={'text':'tai nghe Beats','reset':True})
    assert response.status_code==200,response.text
    assert 79 in [p['articleID'] for p in response.json()['products']]

def test_selected_image_type_is_enforced_through_http_and_persisted(app_client):
    from bootstrap import create_app
    from Model.application.ai.IntentExtractorService import IntentExtractorService
    from Model.application.ai.ObjectDetectorService import ObjectDetectorService
    from Model.application.retrieval.representations import metadata
    from Model.application.config.settings import ROOT
    client,original=app_client;db=original.state.services['db']
    ids=[1,41,61,81]
    before=db.query('SELECT articleID,imageEmbedding,textEmbedding FROM Products WHERE articleID IN (1,41,61,81)')
    query=[1.0]+[0.0]*511
    class Encoder:
        identity=metadata()['identity']
        def encodeImage(self,image):return query
        def encodeText(self,text):return query
    class Detector:
        def detectProducts(self,image):
            return [{'label':'a tablet computer','score':.9,'region':[0,0,.5,.5]},
                    {'label':'a mobile phone','score':.8,'region':[.5,0,1,.5]},
                    {'label':'headphones','score':.8,'region':[0,.5,.5,1]}]
        def cropRegion(self,image,region):return ObjectDetectorService().cropRegion(image,region)
    try:
        for articleID in ids:
            vector=([.4,.9165]+[0.0]*510) if articleID==41 else query
            db.query('UPDATE Products SET imageEmbedding=%s,textEmbedding=%s WHERE articleID=%s',(json.dumps(vector),json.dumps(vector),articleID))
        app=create_app(db.options['database'],{'embedder':Encoder(),'detector':Detector(),'intent':IntentExtractorService()})
        source=original.state.services['products'].findById(1)
        content=(ROOT/source['imagePath']).read_bytes()
        with TestClient(app) as image_client:
            files=lambda:{'file':('multiple.jpg',content,'image/jpeg')}
            detected=image_client.post('/api/search/detect',files=files()).json()
            assert [r['categoryID'] for r in detected['regions']]==[3,1,4]
            result=image_client.post('/api/search/image',files=files(),data={'region':'[0,0,0.5,0.5]','imageCategoryID':'3'})
            assert result.status_code==200,result.text
            body=result.json();assert [p['articleID'] for p in body['products']]==[41]
            assert body['criteria']['categoryID']==body['imageSelection']['categoryID']==3
            assert db.query('SELECT searchCriteria FROM searchQueries WHERE queryID=%s',(body['queryID'],),one=True)['searchCriteria']['categoryID']==3
            assert db.query('SELECT selectedRegion FROM imageQueries WHERE queryID=%s',(body['queryID'],),one=True)['selectedRegion']==[0,0,.5,.5]
            # A manual phone correction changes the candidate category, not the crop.
            corrected=image_client.post('/api/search/image',files=files(),data={'region':'[0,0,0.5,0.5]','imageCategoryID':'1'})
            assert corrected.status_code==200 and {p['categoryID'] for p in corrected.json()['products']}=={1}
            for conflicting in [{'categoryID':'5'},{'text':'điện thoại'}]:
                result=image_client.post('/api/search/image',files=files(),data={'region':'[0,0,0.5,0.5]','imageCategoryID':'3',**conflicting})
                assert result.status_code==400
            assert image_client.post('/api/search/image',files=files(),data={'imageCategoryID':'99'}).status_code==422
    finally:
        for row in before:
            db.query('UPDATE Products SET imageEmbedding=%s,textEmbedding=%s WHERE articleID=%s',
                     (json.dumps(row['imageEmbedding']) if row['imageEmbedding'] is not None else None,
                      json.dumps(row['textEmbedding']) if row['textEmbedding'] is not None else None,row['articleID']))

def test_gemini_voice_to_validated_criteria_and_persisted_subtype(app_client,monkeypatch):
    import httpx
    from bootstrap import create_app
    from Model.application.ai.GeminiClient import GeminiClient
    client,original=app_client
    monkeypatch.setenv('APP_INTENT_PROVIDER','gemini');monkeypatch.setenv('APP_TRANSCRIBE_PROVIDER','gemini')
    seen=[]
    def handler(request):
        payload=json.loads(request.content);parts=payload['contents'][0]['parts']
        audio=any('inlineData' in p for p in parts);seen.append('audio' if audio else 'intent')
        answer={'transcript':'điện thoại Samsung dưới 40 triệu'} if audio else {'supported':True,'categoryID':1,'brand':'Samsung','maxPrice':40_000_000}
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(answer,ensure_ascii=False)}]}}]})
    provider=GeminiClient(lambda:{'APP_GEMINI_API_KEY':'test-key'},lambda **kw:httpx.Client(transport=httpx.MockTransport(handler),**kw))
    app=create_app(original.state.services['db'].options['database'],{'gemini':provider,'embedder':original.state.services['embedder']})
    with TestClient(app) as gemini_client:
        transcription=gemini_client.post('/api/search/transcribe',files={'file':('recording.webm',b'audio-fixture','audio/webm')})
        assert transcription.status_code==200,transcription.text
        search=gemini_client.post('/api/search/text',headers={'X-Search-Context':uuid.uuid4().hex},json={'text':transcription.json()['text'],'queryType':'voice','reset':True})
        assert search.status_code==200,search.text
        data=search.json();assert data['criteria']['intentProvider']=='gemini'
        assert data['products'] and all(p['brand']=='Samsung' and float(p['price'])<=40_000_000 for p in data['products'])
        qid=data['queryID'];db=app.state.services['db']
        assert db.query('SELECT * FROM voiceQueries WHERE queryID=%s',(qid,),one=True)
        assert not db.query('SELECT * FROM textQueries WHERE queryID=%s',(qid,),one=True)
        assert db.query('SELECT searchCriteria FROM searchQueries WHERE queryID=%s',(qid,),one=True)['searchCriteria']['intentProvider']=='gemini'
        assert gemini_client.get('/api/health').json()['transcriptionProvider']=='gemini'
    assert seen==['audio','intent']

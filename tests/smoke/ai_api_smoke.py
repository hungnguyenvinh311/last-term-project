"""Full HTTP/DAO/model integration in the isolated test database only."""
import sys,json,uuid,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from Model.application.config.settings import ROOT
from bootstrap import create_app
from DAO.application.dao.connection import Database
from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
from crawler.storage.files import save_json

def run():
    name=json.loads((ROOT/'data/test_runs/latest_mysql_test.json').read_text())['database']
    if not name.startswith('ecommerce_test_'):raise RuntimeError('Refuse writes outside isolated test DB')
    source=ProductDAOImpl(Database());target=ProductDAOImpl(Database(name))
    for p in source.findActive(): target.saveRepresentation(p['articleID'],p['imageEmbedding'],p['textEmbedding'])
    from Model.application.ai.IntentExtractorService import IntentExtractorService
    app=create_app(name,{'intent':IntentExtractorService()})
    image_calls=[]
    encode_image=app.state.services['embedder'].encodeImage
    def counted_image(image):
        image_calls.append(1);return encode_image(image)
    app.state.services['embedder'].encodeImage=counted_image
    start=time.perf_counter()
    with TestClient(app) as client:
        headers={'X-Search-Context':uuid.uuid4().hex}
        text=client.post('/api/search/text',headers=headers,json={'text':'điện thoại Samsung dưới 40 triệu','reset':True})
        assert text.status_code==200,text.text
        assert text.json()['products'] and text.json()['fallback'] is False
        p=source.findActive()[0];content=(ROOT/p['imagePath']).read_bytes()
        image=client.post('/api/search/image',files={'file':('query.jpg',content,'image/jpeg')})
        assert image.status_code==200,image.text
        assert p['articleID'] in [r['articleID'] for r in image.json()['products'][:5]]
        crop=client.post('/api/search/image',files={'file':('query.jpg',content,'image/jpeg')},data={'region':'[0,0,0.99,0.99]','imageCategoryID':str(p['categoryID'])})
        assert crop.status_code==200,crop.text
        combined=client.post('/api/search/image',files={'file':('query.jpg',content,'image/jpeg')},data={'text':'dưới 40 triệu','brand':'Samsung','categoryID':'1'})
        assert combined.status_code==200,combined.text
        assert combined.json()['products']
        assert all(p['brand']=='Samsung' and p['categoryID']==1 and float(p['price'])<=40_000_000 for p in combined.json()['products'])
        combined_query=target.db.query('SELECT searchCriteria FROM searchQueries WHERE queryID=%s',(combined.json()['queryID'],),one=True)['searchCriteria']
        assert combined_query['text']=='dưới 40 triệu' and combined_query['brand']=='Samsung'
        assert len(image_calls)==2, 'Whole-image and crop should encode once each'
        warm_start=time.perf_counter()
        repeated=client.post('/api/search/image',files={'file':('query.jpg',content,'image/jpeg')},data={'text':combined_query['text'],'brand':'Samsung','categoryID':'1'})
        warm_seconds=time.perf_counter()-warm_start
        assert repeated.status_code==200 and repeated.json()['products']
        assert len(image_calls)==2, 'Filter replay must reuse image embedding'
        assert all('matchDetails' in row for row in repeated.json()['products'])
        # Golden consistency cases from manually inspected representative photos.
        orange=client.post('/api/search/text',headers={'X-Search-Context':uuid.uuid4().hex},json={'text':'điện thoại màu cam','reset':True})
        assert orange.status_code==200,orange.text
        assert {row['articleID'] for row in orange.json()['products']}=={2,14,16},orange.text
        assert all(row['matchDetails']['weights']==[.55,0,.45] for row in orange.json()['products'])
        changed_colour=client.post('/api/search/image',files={'file':('purple-phone.jpg',content,'image/jpeg')},data={'text':'điện thoại màu cam'})
        assert changed_colour.status_code==200,changed_colour.text
        assert {row['articleID'] for row in changed_colour.json()['products']}=={2,14,16},changed_colour.text
        assert all(row['matchDetails']['weights']==[.6,.25,.15] for row in changed_colour.json()['products'])
        restricted=client.post('/api/search/image',files={'file':('purple-phone.jpg',content,'image/jpeg')},data={'text':'điện thoại màu cam','brand':'Apple'})
        assert restricted.status_code==200,restricted.text
        assert {row['articleID'] for row in restricted.json()['products']}=={14,16}
        unknown_colour=client.post('/api/search/text',headers={'X-Search-Context':uuid.uuid4().hex},json={'text':'điện thoại màu xanh lá','reset':True})
        assert unknown_colour.status_code==200 and unknown_colour.json()['products']==[]
        detected=client.post('/api/search/detect',files={'file':('query.jpg',content,'image/jpeg')})
        assert detected.status_code==200 and detected.json()['fallback'] is False,detected.text
        assert detected.json()['regions']
        assert all(region['categoryID'] in range(1,6) for region in detected.json()['regions'])
        # Controlled multi-product query: real catalogue phone, tablet and headphones.
        # Known crop coordinates test retrieval scope independently of detector accuracy.
        from PIL import Image,ImageOps
        from io import BytesIO
        composite=Image.new('RGB',(900,300),'white')
        catalogue={row['articleID']:row for row in source.findActive()}
        for index,articleID in enumerate((1,41,61)):
            with Image.open(ROOT/catalogue[articleID]['imagePath']) as photo:
                tile=ImageOps.contain(photo.convert('RGB'),(300,300))
                composite.paste(tile,(index*300+(300-tile.width)//2,(300-tile.height)//2))
        buffer=BytesIO();composite.save(buffer,format='PNG');multi=buffer.getvalue()
        for selected_category,region,expected_source in [(3,[1/3,0,2/3,1],41),(1,[0,0,1/3,1],1),(4,[2/3,0,1,1],61)]:
            chosen=client.post('/api/search/image',files={'file':('three-products.png',multi,'image/png')},data={'region':json.dumps(region),'imageCategoryID':str(selected_category)})
            assert chosen.status_code==200,chosen.text
            products=chosen.json()['products'];assert products,chosen.text
            assert all(row['categoryID']==selected_category for row in products),chosen.text
            assert expected_source in [row['articleID'] for row in products[:5]],chosen.text
            assert chosen.json()['imageSelection']['categoryID']==selected_category
        recommendation=client.get(f'/api/products/{p["articleID"]}/recommendations').json()
        assert recommendation['fallback'] is False and len(recommendation['products'])==8
        qid=image.json()['queryID']
        assert target.db.query('SELECT * FROM imageQueries WHERE queryID=%s',(qid,),one=True)
        assert not target.db.query('SELECT * FROM textQueries WHERE queryID=%s',(qid,),one=True)
    save_json(ROOT/'data/test_runs/real_ai_api_report.json',{'database':name,'passed':True,'textRealEncoder':True,'imageRealEncoder':True,'imageAndTextWithBrandPriceFilter':True,'threeProductCompositeSelectedCategories':[3,1,4],'selectedCategoryNoCrossTypeResults':True,'detectorCategoryIDsChecked':True,'orangeTextIDs':[2,14,16],'orangeChangeFromPurpleIDs':[2,14,16],'orangeAppleIDs':[14,16],'noAnnotatedGreenPhonesReturnsEmpty':True,'liveWeightPoliciesChecked':True,'colourLabelScope':'assistant visual consistency labels; not independent accuracy benchmark','crop':True,'detectedRegions':len(detected.json()['regions']),'recommendationNoFallback':True,'imageSubtypeStored':True,'warmCombinedSeconds':warm_seconds,'imageEncoderCalls':len(image_calls),'seconds':time.perf_counter()-start,'voiceAPI':'not called; requires user key and reviewed audio'})
    print('Real AI HTTP integration passed in isolated MySQL test database.')

if __name__=='__main__':run()

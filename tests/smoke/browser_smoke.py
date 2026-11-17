"""Browser E2E on an isolated database named by integration tests."""
import sys,os,json,time,subprocess,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from playwright.sync_api import sync_playwright,expect
from urllib.request import urlopen
from crawler.storage.files import save_json

def run():
    report=json.loads((ROOT/'data/test_runs/latest_mysql_test.json').read_text(encoding='utf-8'))
    if not report['database'].startswith('ecommerce_test_'): raise RuntimeError('Refuse browser writes outside test DB')
    env=dict(os.environ,APP_DATABASE=report['database'],APP_INTENT_PROVIDER='rules',PYTHONIOENCODING='utf-8')
    output=ROOT/'data/test_runs/browser_server.log'
    with output.open('w',encoding='utf-8') as log:
        server=subprocess.Popen([sys.executable,'-m','uvicorn','bootstrap:app','--host','127.0.0.1','--port','8018'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(50):
                try:
                    with urlopen('http://127.0.0.1:8018/api/health',timeout=1) as response:
                        if response.status==200: break
                except Exception: time.sleep(.3)
            with sync_playwright() as p:
                edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
                browser=p.chromium.launch(executable_path=str(edge),headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1000})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:8018',wait_until='networkidle')
                expect(page.locator('article.product')).to_have_count(100)
                records=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
                from Model.application.ai.product_caption import PHOTO_COLOR_KEY
                expect(page.locator('.photo-colour')).to_have_count(sum(PHOTO_COLOR_KEY in (p.get('technicalSpecs') or {}) for p in records))
                page.get_by_role('combobox',name='Thương hiệu',exact=True).select_option('Samsung')
                expect(page.locator('article.product')).to_have_count(sum(p['brand']=='Samsung' for p in records))
                page.get_by_role('button',name='Xóa tìm kiếm và bộ lọc').click()
                expect(page.locator('article.product')).to_have_count(100)
                page.locator('input[type=file]').set_input_files(str(ROOT/records[0]['imagePath']))
                expect(page.get_by_role('textbox',name='Yêu cầu tìm kiếm')).to_be_enabled()
                page.get_by_role('textbox',name='Yêu cầu tìm kiếm').fill('Samsung dưới 40 triệu')
                expect(page.get_by_role('textbox',name='Yêu cầu tìm kiếm')).to_have_value('Samsung dưới 40 triệu')
                # Controlled detector response verifies UI geometry, selection and rank legend.
                page.route('**/api/search/detect',lambda route:route.fulfill(json={'regions':[
                    {'label':'a mobile phone','categoryID':1,'score':.91,'region':[.1,.2,.8,.9]},
                    {'label':'a tablet computer','categoryID':3,'score':.85,'region':[.2,.1,.9,.8]},
                    {'label':'headphones','categoryID':4,'score':.80,'region':[.4,.3,.9,.9]}],'fallback':False}))
                page.get_by_role('button',name='Nhận diện sản phẩm trong ảnh').click()
                box=page.get_by_role('button',name='Select region 1')
                expect(box).to_be_visible()
                preview=page.locator('.detection-preview>img').bounding_box();bounds=box.locator('..').bounding_box()
                assert abs(bounds['x']-(preview['x']+.1*preview['width']))<2
                assert abs(bounds['width']-.7*preview['width'])<2
                image_type=page.get_by_role('combobox',name='Loại sản phẩm trong ảnh',exact=True)
                expect(image_type).to_have_value('0')
                page.get_by_role('button',name='Select region 2').click()
                expect(image_type).to_have_value('3')
                expect(page.get_by_role('status').filter(has_text='Chỉ tìm trong nhóm: Máy tính bảng')).to_be_visible()
                # Manual correction keeps the same crop; the correction is submitted.
                image_type.select_option('1')
                expect(page.get_by_role('button',name='Select region 2').locator('..')).to_have_class('detection-box chosen')
                box.click();expect(box.locator('..')).to_have_class('detection-box chosen')
                captured=[]
                fixture=dict(records[0],imageUrl='/api/products/'+str(records[0]['articleID'])+'/image',matchDetails={'metric':'cosine','embedding':.8,'text':.3,'keyword':.5,'rankScore':.64,'mode':'image+text'})
                def image_response(route):
                    captured.append(route.request.post_data_buffer)
                    route.fulfill(json={'products':[fixture],'message':'UI fixture','criteria':{},'fallback':False})
                page.route('**/api/search/image',image_response)
                page.get_by_role('button',name='Tìm kiếm →').click()
                expect(page.locator('.match-legend')).to_have_count(1)
                expect(page.locator('.match-legend')).to_contain_text('0.800')
                expect(page.locator('.match-legend')).to_contain_text('0.300')
                expect(page.locator('.match-legend')).to_contain_text('0.640')
                expect(page.locator('.photo-colour')).to_have_text('Màu ảnh: Tím')
                assert b'[0.1,0.2,0.8,0.9]' in captured[0]
                assert b'name="imageCategoryID"\r\n\r\n1\r\n' in captured[0]
                # Submit a corrected class while retaining the detected tablet crop.
                page.get_by_role('button',name='Select region 2').click()
                image_type.select_option('1')
                with page.expect_response('**/api/search/image'):
                    page.get_by_role('button',name='Tìm kiếm →').click()
                assert len(captured)==2
                assert b'[0.2,0.1,0.9,0.8]' in captured[1]
                assert b'name="imageCategoryID"\r\n\r\n1\r\n' in captured[1]
                page.get_by_role('combobox',name='Vùng tìm kiếm',exact=True).select_option('')
                expect(image_type).to_have_value('0')
                with page.expect_response('**/api/search/image'):
                    page.get_by_role('button',name='Tìm kiếm →').click()
                assert len(captured)==3 and b'name="imageCategoryID"' not in captured[2] and b'name="region"' not in captured[2]
                page.screenshot(path=str(ROOT/'data/test_runs/search_regions_legend.png'))
                page.unroute('**/api/search/detect');page.unroute('**/api/search/image')
                page.get_by_role('button',name='Xóa tìm kiếm và bộ lọc').click()
                page.wait_for_function("Array.from(document.querySelectorAll('.product img')).slice(0,5).every(i=>i.complete && i.naturalWidth>0)")
                page.screenshot(path=str(ROOT/'data/test_runs/mainview_desktop.png'),full_page=False)
                page.get_by_role('button',name='Đăng nhập',exact=True).click()
                page.get_by_role('button',name='Chưa có tài khoản? Đăng ký').click()
                page.get_by_label('Họ tên',exact=True).fill('Browser Test')
                email='browser-'+uuid.uuid4().hex[:8]+'@example.test'
                page.get_by_label('Email',exact=True).fill(email)
                page.get_by_label('Mật khẩu',exact=True).fill('browser-password-123')
                page.get_by_role('button',name='Đăng ký',exact=True).click()
                expect(page.get_by_role('heading',name='Chào mừng trở lại')).to_be_visible()
                page.get_by_label('Email',exact=True).fill(email)
                page.get_by_label('Mật khẩu',exact=True).fill('browser-password-123')
                page.locator('.dialog').get_by_role('button',name='Đăng nhập',exact=True).click()
                expect(page.get_by_role('button',name=email,exact=True)).to_be_visible()
                page.get_by_role('textbox',name='Yêu cầu tìm kiếm').fill('điện thoại Samsung dưới 40 triệu')
                page.get_by_role('button',name='Tìm kiếm →').click()
                expect(page.locator('.product').first).to_be_visible()
                expect(page.get_by_role('status').filter(has_text='Tìm theo từ khóa')).to_be_visible()
                page.locator('.product .image-button').first.click()
                expect(page.locator('.dialog.wide .detail')).to_be_visible()
                expect(page.locator('.dialog.wide .product')).to_have_count(8)
                page.locator('.detail').get_by_role('button',name='Thêm vào giỏ',exact=True).click()
                expect(page.get_by_role('status').filter(has_text='Đã thêm vào giỏ hàng')).to_be_visible()
                page.locator('.dialog.wide .close').click()
                page.get_by_role('button',name='Giỏ hàng',exact=True).click()
                expect(page.locator('.cart-row')).to_have_count(1)
                page.get_by_role('button',name='Tiến hành đặt hàng →').click()
                page.get_by_label('Địa chỉ nhận hàng',exact=True).fill('Browser demo street 123')
                page.get_by_label('Số điện thoại',exact=True).fill('0901234567')
                page.get_by_label('Tôi xác nhận sản phẩm, giá và thông tin nhận hàng').check()
                page.get_by_role('button',name='Xác nhận đặt hàng',exact=True).click()
                expect(page.get_by_role('heading',name='Đơn hàng của bạn')).to_be_visible()
                expect(page.locator('.order-row')).to_have_count(1)
                page.get_by_role('button',name='Xem chi tiết',exact=True).click()
                expect(page.locator('.dialog')).to_contain_text('UnpaidCOD')
                page.locator('.dialog .close').click()
                page.get_by_role('button',name='Khám phá',exact=True).click()
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(ROOT/'data/test_runs/mainview_mobile.png'),full_page=False)
                assert not errors,errors
                save_json(ROOT/'data/test_runs/browser_report.json',{'database':report['database'],'passed':True,'steps':['catalogue100','brand_filter_and_clear','image_text_input_enabled','register','login','text_search','detail','recommendation8','cart','checkoutCOD','order_detail','mobile_render'],'page_errors':errors})
                browser.close()
        finally:
            server.terminate();server.wait(timeout=15)
    print('Browser E2E passed; report and screenshots saved under data/test_runs.')

if __name__=='__main__':run()

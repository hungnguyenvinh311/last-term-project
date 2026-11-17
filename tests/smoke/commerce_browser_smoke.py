"""Real browser acceptance of the new commerce screens; writes only to retained test DB."""
import json,os,subprocess,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from playwright.sync_api import sync_playwright,expect
from urllib.request import urlopen
from bootstrap import create_app
from scripts.schema_snapshot import snapshot

def run():
    name=json.loads((ROOT/'data/test_runs/latest_commerce_test.json').read_text(encoding='utf-8'))['database']
    if not name.startswith('ecommerce_test_'): raise RuntimeError('Test database required')
    app=create_app(name);db=app.state.services['db'];before=snapshot(db)
    service=app.state.services['accounts'];password=uuid.uuid4().hex
    email='browser-staff-'+uuid.uuid4().hex[:8]+'@example.test'
    service.createStaff(email,password,'Browser staff')
    token=service.login(email,password)['token']
    artifacts=ROOT/'data/test_runs'
    code='''import os,uvicorn
from bootstrap import create_app
from Model.application.config.settings import ROOT
from Model.application.integration.storage.LocalMediaStorage import LocalMediaStorage
from Model.application.errors import DomainError
class TestMedia(LocalMediaStorage):
    def resolveProductImage(self,reference):
        try: return super().resolveProductImage(reference)
        except DomainError: return LocalMediaStorage(ROOT).resolveProductImage(reference)
uvicorn.run(create_app(os.environ['APP_DATABASE'],{'media':TestMedia(ROOT/'data/test_runs/commerce_browser_media')}),host='127.0.0.1',port=8019)
'''
    env=dict(os.environ,APP_DATABASE=name,APP_INTENT_PROVIDER='rules',PYTHONIOENCODING='utf-8')
    steps=[]
    with (artifacts/'commerce_browser_server.log').open('w',encoding='utf-8') as log:
        server=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(80):
                try:
                    if urlopen('http://127.0.0.1:8019/api/health',timeout=1).status==200: break
                except Exception: time.sleep(.25)
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
                page=context.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.add_init_script('sessionStorage.setItem("token",'+json.dumps(token)+')')
                page.goto('http://127.0.0.1:8019',wait_until='networkidle')
                page.get_by_role('button',name='Nhân viên',exact=True).click()
                page.get_by_role('button',name='Sản phẩm và danh mục',exact=True).click()
                page.get_by_role('button',name='Thêm sản phẩm',exact=True).click()
                dialog=page.locator('.dialog')
                product_name='Browser product '+uuid.uuid4().hex[:6]
                dialog.get_by_label('Tên sản phẩm',exact=True).fill(product_name)
                dialog.get_by_label('Thương hiệu',exact=True).fill('BrowserBrand')
                dialog.get_by_label('Giá VND',exact=True).fill('1230000')
                dialog.get_by_label('Thông số (JSON)',exact=True).fill('{"screen":"6 inch","color":"blue"}')
                dialog.get_by_label('Bảo hành',exact=True).fill('12 months')
                image_path=artifacts/'commerce_upload.png'
                from PIL import Image
                Image.new('RGB',(40,40),'blue').save(image_path)
                dialog.locator('input[type=file]').set_input_files(str(image_path))
                with page.expect_response('**/api/staff/catalogue/products') as saved:
                    dialog.get_by_role('button',name='Lưu sản phẩm',exact=True).click()
                assert saved.value.status==201,saved.value.json()
                expect(page.locator('.dialog')).to_have_count(0)
                page.get_by_role('textbox',name='Tìm sản phẩm quản trị').fill(product_name)
                row=page.locator('tbody tr').filter(has_text=product_name)
                expect(row).to_have_count(1)
                row.get_by_role('button',name='Sửa',exact=True).click()
                dialog.get_by_label('Giá VND',exact=True).fill('1300000')
                dialog.get_by_role('button',name='Lưu sản phẩm',exact=True).click()
                expect(page.locator('.dialog')).to_have_count(0)
                expect(row).to_contain_text('1.300.000')
                steps.append('catalogue_create_upload_edit')
                # Seed a real COD order using the customer API, then operate it through UI.
                response=page.request.post('http://127.0.0.1:8019/api/accounts/register',data={'email':'buyer-'+uuid.uuid4().hex[:8]+'@example.test','password':password,'fullName':'Browser Buyer'})
                assert response.status==201
                buyer=page.request.post('http://127.0.0.1:8019/api/accounts/login',data={'email':response.json()['email'],'password':password}).json()
                headers={'Authorization':'Bearer '+buyer['token']}
                product=next(r for r in page.request.get('http://127.0.0.1:8019/api/products').json() if r['productName']==product_name)
                assert page.request.post('http://127.0.0.1:8019/api/cart/items',headers=headers,data={'articleID':product['articleID'],'quantity':1}).status==200
                order=page.request.post('http://127.0.0.1:8019/api/orders',headers=headers,data={'paymentMethod':'COD','shippingAddress':'Browser delivery street 123','recipientPhone':'0901234567','prices':{str(product['articleID']):product['price']}})
                assert order.status==201
                oid=order.json()['orderID']
                page.get_by_role('button',name='Đơn hàng',exact=True).last.click()
                page.get_by_role('textbox',name='Mã đơn',exact=True).fill(str(oid))
                page.locator('.order-row').filter(has=page.get_by_text('#'+str(oid),exact=True)).get_by_role('button',name='Xem chi tiết',exact=True).click()
                for action,state in [('Bắt đầu đóng gói','Packing'),('Hoàn tất đóng gói','Packed'),('Xuất giao','Dispatched'),('Xác nhận đã giao','Delivered')]:
                    with page.expect_response('**/api/staff/orders/'+str(oid)+'/shipment'):
                        dialog.get_by_role('button',name=action,exact=True).click()
                    expect(dialog).to_contain_text(state)
                dialog.get_by_label('Mã xác nhận duy nhất',exact=True).fill('BROWSER-COD-'+str(oid))
                dialog.get_by_role('button',name='Xác nhận COD',exact=True).click()
                expect(dialog).to_contain_text('Paid')
                expect(dialog.get_by_role('button',name='Xác nhận COD',exact=True)).to_have_count(0)
                page.screenshot(path=str(artifacts/'commerce_order_cod.png'))
                dialog.locator('.close').click()
                steps.append('fulfilment_packing_packed_dispatch_customer_delivery_cod')
                page.get_by_role('button',name='Tài khoản',exact=True).click()
                page.get_by_label('Họ tên',exact=True).fill('Created by Browser')
                page.get_by_label('Email',exact=True).fill('created-'+uuid.uuid4().hex[:8]+'@example.test')
                page.get_by_label('Mật khẩu khởi tạo',exact=True).fill(uuid.uuid4().hex)
                page.get_by_role('button',name='Tạo nhân viên',exact=True).click()
                expect(page.locator('.order-row').filter(has_text='Created by Browser')).to_have_count(1)
                steps.append('staff_create')
                page.get_by_role('button',name='Báo cáo',exact=True).click()
                page.get_by_role('button',name='Tạo báo cáo',exact=True).click()
                expect(page.get_by_role('button',name='Xuất CSV',exact=True)).to_be_visible()
                expect(page.get_by_text('Số đơn: 0 · Số sản phẩm bán: 0',exact=True)).to_have_count(0)
                expect(page.locator('tbody tr').filter(has_text=product_name)).to_have_count(1)
                for fmt,label in [('csv','Xuất CSV'),('pdf','Xuất PDF')]:
                    with page.expect_download() as info:
                        page.get_by_role('button',name=label,exact=True).click()
                    info.value.save_as(str(artifacts/('commerce_sales.'+fmt)))
                page.screenshot(path=str(artifacts/'commerce_reports.png'))
                steps.append('report_json_csv_pdf')
                # Customer profile on another browser context, including date of birth.
                customer_context=browser.new_context(viewport={'width':390,'height':844})
                customer_page=customer_context.new_page()
                customer_page.add_init_script('sessionStorage.setItem("token",'+json.dumps(buyer['token'])+')')
                customer_page.goto('http://127.0.0.1:8019',wait_until='networkidle')
                customer_page.get_by_role('button',name=buyer['account']['email'],exact=True).click()
                customer_page.get_by_label('Ngày sinh',exact=True).fill('2000-01-01')
                customer_page.get_by_label('Địa chỉ mặc định',exact=True).fill('New profile street 456')
                customer_page.get_by_role('button',name='Lưu hồ sơ',exact=True).click()
                expect(customer_page.get_by_role('status')).to_contain_text('Đã cập nhật hồ sơ')
                customer_page.screenshot(path=str(artifacts/'commerce_profile_mobile.png'))
                steps.append('customer_profile_mobile')
                assert not errors,errors
                browser.close()
                assert snapshot(db)==before
                (artifacts/'commerce_browser_report.json').write_text(json.dumps({'database':name,'passed':True,'steps':steps,'page_errors':errors,'schemaUnchanged':True},indent=2),encoding='utf-8')
        finally:
            server.terminate();server.wait(timeout=20)
    print('Commerce browser E2E passed; evidence in data/test_runs.')

if __name__=='__main__': run()

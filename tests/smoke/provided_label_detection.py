"""Read-only browser check of original-image geometry with real assisted detection."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from playwright.sync_api import sync_playwright,expect


def run():
    pairs=json.loads((ROOT/'data/pairwise_search_tests/report.json').read_text(encoding='utf-8'))
    pair=next(p for p in pairs['pairs'] if p['pairID']=='tablet__watch')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
        page=browser.new_page(viewport={'width':1400,'height':1000})
        page.goto('http://127.0.0.1:8008',wait_until='networkidle')
        page.locator('input[type=file]').set_input_files(str(ROOT/'data/pairwise_search_tests'/pair['queryImage']))
        image=page.locator('.detection-preview>img')
        expect(image).to_be_visible()
        original_src=image.get_attribute('src')
        with page.expect_response('**/api/search/detect',timeout=180000) as pending:
            page.get_by_role('button',name='Nhận diện sản phẩm trong ảnh').click()
        response=pending.value; assert response.status==200
        result=response.json();expect(page.locator('.detection-box')).to_have_count(2)
        assert image.get_attribute('src')==original_src
        dimensions=image.evaluate('(img)=>[img.naturalWidth,img.naturalHeight]')
        assert dimensions==[1200,600]
        assert [r['categoryID'] for r in result['regions']]==[3,5]
        assert result['regions'][0]['sourceTransform']=='rotate270cw'
        assert result['regions'][1]['sourceTransform']=='original'
        bounds=image.bounding_box()
        for index,region in enumerate(result['regions']):
            actual=page.locator('.detection-box').nth(index).bounding_box();x1,y1,x2,y2=region['region']
            assert abs(actual['x']-(bounds['x']+x1*bounds['width']))<2
            assert abs(actual['y']-(bounds['y']+y1*bounds['height']))<2
            assert abs(actual['width']-(x2-x1)*bounds['width'])<2
            assert abs(actual['height']-(y2-y1)*bounds['height'])<2
        page.get_by_role('button',name='Select region 1').click()
        expect(page.get_by_role('combobox',name='Loại sản phẩm trong ảnh',exact=True)).to_have_value('3')
        assert image.get_attribute('src')==original_src
        page.screenshot(path=str(ROOT/'data/test_runs/provided_labels_browser.png'),full_page=True)
        save_json(ROOT/'data/test_runs/provided_labels_browser.json',{'status':'passed','originalDimensions':dimensions,
            'regions':result['regions'],'originalImagePreserved':True,'screenCoordinatesVerified':True})
        browser.close()
    print('Real browser: original image preserved, two boxes correctly positioned, tablet selection valid.')


if __name__=='__main__':run()

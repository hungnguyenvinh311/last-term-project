import pytest
from crawler.retailer_catalog import ProductLinks,import_catalog,category_matches_name

def test_listing_parser_supports_both_public_layouts():
    parser=ProductLinks()
    parser.feed('<a class="product__link button__link" href="/one.html">One</a>'
                '<a class="block h-fit w-full py-0" href="/two.html">Two</a>'
                '<a class="navigation" href="/not-a-product.html">Menu</a>'
                '<a class="block h-fit w-full" href="/category/brand.html">Brand group</a>')
    assert parser.links==['/one.html','/two.html']

def test_smartbands_and_watch_accessories_are_not_smartwatches():
    assert not category_matches_name('Smartwatch','Vòng đeo tay thông minh Xiaomi Mi Band 11')
    assert not category_matches_name('Smartwatch','Dây đeo Apple Watch')
    assert category_matches_name('Smartwatch','Đồng hồ thông minh Huawei Watch Fit 5 Dây Cao Su')

def test_retailer_import_cannot_target_original_database(monkeypatch):
    import crawler.retailer_catalog as catalog
    monkeypatch.setattr(catalog,'database_options',lambda:{'database':'original_catalog'})
    with pytest.raises(ValueError,match='differ'):
        import_catalog('original_catalog')

def test_validation_detects_image_assigned_to_wrong_product(tmp_path,monkeypatch):
    import crawler.retailer_catalog as catalog
    from PIL import Image
    from crawler.media.images import validate_image
    from crawler.storage.files import save_json
    folder=tmp_path/'data/retailer_catalog';image=folder/'images/fixture.png'
    image.parent.mkdir(parents=True)
    Image.new('RGB',(100,100),'blue').save(image)
    metadata=validate_image(image.read_bytes());relative=image.relative_to(tmp_path).as_posix()
    save_json(folder/'products.json',[dict(articleID=1,categoryID=1,productName='Unit-test fixture',
        brand=None,technicalSpecs=None,imagePath=relative,price='1.00',currency='VND')])
    save_json(folder/'provenance.json',[dict(articleID=1)])
    save_json(folder/'images_manifest.json',[dict(articleID=2,local_path=relative,**metadata)])
    monkeypatch.setattr(catalog,'ROOT',tmp_path);monkeypatch.setattr(catalog,'FOLDER',folder)
    report=catalog.validate()
    assert report['main_image_ownership_mismatches']==[1]
    assert report['orphan_images']==[relative]

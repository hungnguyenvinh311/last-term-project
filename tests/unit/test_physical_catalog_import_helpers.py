from scripts.import_catalog_to_physical_schema import _key, _specs, _stock, _subtype, _subtype_values, _specs_or_array


def test_stock_is_read_from_vietnamese_inventory_attribute():
    quantity, key = _stock({'Số lượng khả dụng (minh họa)': '14'})
    assert quantity == 14
    assert key == 'Số lượng khả dụng (minh họa)'


def test_stock_rejects_negative_boolean_and_fractional_values():
    assert _stock({'quantity': -2}) == (None, None)
    assert _stock({'stock': True}) == (None, None)
    assert _stock({'Số lượng tồn kho': '2.5'}) == (None, None)


def test_product_subtypes_match_the_five_electronics_categories():
    assert [_subtype(name) for name in ('Smartphone', 'Laptop', 'Tablet', 'Smartwatch', 'Headphones')] == [
        'MobilePhone', 'Laptop', 'Tablet', 'SmartWatch', 'Headphones']


def test_subtype_required_fields_receive_safe_defaults():
    assert _subtype_values('Tablet', {'stylusSupport': 'yes'}) == ('Not specified', 1)
    assert _subtype_values('Headphones', {}) == ('Not specified',)


def test_json_helpers_keep_only_supported_shapes():
    assert _specs('{"model":"X"}') == {'model': 'X'}
    assert _specs('[1,2]') == {}
    assert _specs_or_array('[0.1, 0.2]') == [0.1, 0.2]
    assert _specs_or_array('{"not":"a vector"}') == []
    assert _key('Số lượng tồn kho') == 'soluongtonkho'

"""Keep visually reviewed colour evidence before CLIP's finite text context."""
import json
PHOTO_COLOR_KEY='Màu ảnh đại diện'
CATEGORY={1:'smartphone mobile phone',2:'laptop computer',3:'tablet computer',4:'headphones earbuds',5:'smartwatch wrist watch'}

def product_caption(product):
    specs=product.get('technicalSpecs') or {}
    colour=specs.get(PHOTO_COLOR_KEY)
    prefix=f'representative product colour {colour} ' if colour else ''
    return prefix+' '.join([CATEGORY[product['categoryID']],product['productName'],product.get('brand') or '',json.dumps(specs,ensure_ascii=False)])

import pytest
from scripts.screen_shape_confusion import traits,assess,summarize,plausible_product_box,grouped_summary

def entry(identifier,category,predicted,source='unique'):
    detection=[] if predicted is None else [dict(categoryID=predicted,score=.9,region=[.1,.2,.6,.8])]
    result={'assessment':assess(detection,category,[0,0,1,1])}
    return dict(articleID=identifier,categoryID=category,sourceSHA256=source,traits=traits({'articleID':identifier,'categoryID':category}),original=result,grayscale=result)

def test_phone_top1_is_distinct_from_any_phone_box():
    boxes=[dict(categoryID=5,score=.8,region=[.1,.1,.6,.8]),dict(categoryID=1,score=.5,region=[.1,.1,.6,.8])]
    result=assess(boxes,5,[0,0,1,1])
    assert result['isCorrect'] and not result['isPhone'] and result['anyPhoneProductBox']

def test_tiny_logo_box_does_not_override_main_product_but_is_retained_raw():
    boxes=[dict(categoryID=1,score=.99,region=[.1,.1,.12,.12]),dict(categoryID=5,score=.7,region=[.1,.2,.6,.8])]
    result=assess(boxes,5,[0,0,1,1])
    assert result['strongestAnywhere']['categoryID']==1
    assert result['isCorrect'] and not result['anyPhoneProductBox']
    assert len(boxes)==2

def test_wrong_phone_label_is_not_replaced_by_lower_confidence_correct_label():
    boxes=[dict(categoryID=1,score=.9,region=[.1,.1,.6,.8]),dict(categoryID=3,score=.2,region=[.1,.1,.6,.8])]
    result=assess(boxes,3,[0,0,1,1])
    assert result['isPhone'] and not result['isCorrect'] and result['anyCorrectProductBox']

def test_misses_remain_in_denominator_and_duplicates_have_separate_summary():
    rows=[entry(45,3,1,'same'),entry(54,3,1,'same'),entry(81,5,None,'other')]
    full=summarize(rows,'original');unique=summarize(rows,'original',True)
    assert full['images']==3 and full['phoneTop1Rate']==pytest.approx(2/3) and full['missed']==1
    assert unique['images']==2 and unique['phoneTop1Rate']==.5

def test_square_watches_are_not_mixed_with_round_watch_controls():
    rows=[entry(41,3,1,'a'),entry(81,5,1,'b'),entry(82,5,5,'c')]
    groups=grouped_summary(rows)
    assert groups['rectangularColourful']['original']['productWeighted']['images']==2
    assert groups['roundWatches']['original']['productWeighted']['images']==1
    assert traits({'articleID':103,'categoryID':5})['screenAppearance']=='dark_ui_coloured_accents'

def test_square_padding_preserves_pixels_and_maps_boxes_without_stretching():
    from PIL import Image
    from scripts.pair_letterbox_audit import pad_square,remap_region
    image=Image.new('RGB',(120,60),'red')
    square,offset=pad_square(image)
    assert square.size==(120,120) and offset==(0,30)
    assert square.getpixel((60,60))==(255,0,0) and square.getpixel((60,10))==(255,255,255)
    assert remap_region([0,0,.5,1],image.size,square.size,offset)==[0,.25,.5,.75]

def test_tall_padding_also_preserves_normalized_coordinates():
    from PIL import Image
    from scripts.pair_letterbox_audit import pad_square,remap_region
    image=Image.new('RGB',(60,120),'blue');square,offset=pad_square(image)
    assert offset==(30,0)
    assert remap_region([0,0,1,1],image.size,square.size,offset)==[.25,0,.75,1]

@pytest.mark.parametrize('box',[[0,0,0,.9],[0,0,float('nan'),.8],[-.1,0,.8,.8],[.8,.8,.95,.95]])
def test_invalid_or_outside_product_boxes_rejected(box):
    assert not plausible_product_box({'region':box},[0,0,.6,.8])

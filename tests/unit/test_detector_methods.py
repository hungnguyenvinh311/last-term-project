import pytest
from PIL import Image
from scripts.test_detector_methods_1_2 import flatten_bank,PROMPT_BANK,unpad,category_metrics,pixel_key
from scripts.pair_letterbox_audit import pad_square,remap_region

def test_bank_is_balanced_and_prompt_labels_map_to_business_categories():
    labels,categories=flatten_bank(PROMPT_BANK)
    assert len(labels)==15 and categories==[1]*3+[2]*3+[3]*3+[4]*3+[5]*3
    assert len(set(labels))==15
    assert categories[labels.index('a wristwatch with a strap')]==5
    assert categories[labels.index('a touchscreen tablet device')]==3

def test_unequal_class_prompt_counts_are_rejected():
    bank={k:list(v) for k,v in PROMPT_BANK.items()};bank[3].append('extra tablet')
    with pytest.raises(ValueError):flatten_bank(bank)

@pytest.mark.parametrize('size',[(1200,600),(600,1200),(601,1000),(1000,1000)])
def test_padding_coordinate_roundtrip_preserves_crop(size):
    image=Image.new('RGB',size);padded,offset=pad_square(image)
    original=[.1,.2,.7,.9];mapped=remap_region(original,image.size,padded.size,offset)
    assert unpad(mapped,image.size,padded.size,offset)==pytest.approx(original)

def test_boxes_entirely_in_padding_are_not_mapped_to_fake_objects():
    assert unpad([0,0,1,.2],(1200,600),(1200,1200),(0,300)) is None

def test_square_padding_has_identical_pixels_and_cache_identity():
    image=Image.new('RGB',(100,100),'red');padded,_=pad_square(image)
    assert pixel_key(image,'baseline')==pixel_key(padded,'baseline')
    assert pixel_key(image,'baseline')!=pixel_key(image,'descriptive')

def test_any_correct_label_is_not_counted_as_correct_strongest_box():
    row={'categoryID':3,'sourceSHA256':'a','baseline':{'assessment':{'isCorrect':False,'anyCorrectProductBox':True,'missed':False,'isPhone':True}}}
    result=category_metrics([row],'baseline',3)
    assert result['correctTop1']==0 and result['correctLabelAvailable']==1 and result['count']==1

def test_missing_prediction_remains_in_denominator():
    rows=[{'baseline':{'targets':[{'categoryID':5,'isCorrect':False,'correctAvailable':False,'top':None},{'categoryID':5,'isCorrect':True,'correctAvailable':True,'top':{'categoryID':5}}]}}]
    result=category_metrics(rows,'baseline',5,pairs=True)
    assert result['correctTop1Rate']==.5 and result['missed']==1

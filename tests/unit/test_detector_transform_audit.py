import pytest
from PIL import Image
from tests.experiments.survey_rotations_flips import transform


@pytest.mark.parametrize('variant,expected,size',[
    ('original',[.1,.2,.4,.7],(100,200)),
    ('rotate90cw',[.3,.1,.8,.4],(200,100)),
    ('rotate180',[.6,.3,.9,.8],(100,200)),
    ('rotate270cw',[.2,.6,.7,.9],(200,100)),
    ('flip_horizontal',[.6,.2,.9,.7],(100,200)),
    ('flip_vertical',[.1,.3,.4,.8],(100,200))])
def test_roi_moves_with_image_without_resizing(variant,expected,size):
    original=Image.new('RGB',(100,200)); original.putpixel((15,50),(255,0,0))
    result,roi=transform(original,[.1,.2,.4,.7],variant)
    assert roi==pytest.approx(expected) and result.size==size
    red=[(x,y) for y in range(result.height) for x in range(result.width) if result.getpixel((x,y))==(255,0,0)]
    assert len(red)==1
    x,y=red[0]
    assert roi[0]<=x/result.width<=roi[2] and roi[1]<=y/result.height<=roi[3]
    assert original.getpixel((15,50))==(255,0,0)

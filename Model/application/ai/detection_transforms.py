"""Exact image transposes and normalized-coordinate mappings."""
import hashlib
import math
from PIL import Image

FALLBACK_VIEWS=('rotate270cw','rotate90cw','rotate180','flip_horizontal','flip_vertical')
OPERATIONS={'rotate90cw':Image.Transpose.ROTATE_270,'rotate180':Image.Transpose.ROTATE_180,
            'rotate270cw':Image.Transpose.ROTATE_90,'flip_horizontal':Image.Transpose.FLIP_LEFT_RIGHT,
            'flip_vertical':Image.Transpose.FLIP_TOP_BOTTOM}


def pixel_fingerprint(image):
    rgb=image.convert('RGB')
    return hashlib.sha256(f'{rgb.width}x{rgb.height}:RGB:'.encode()+rgb.tobytes()).hexdigest()


def transform_region(region,view):
    x1,y1,x2,y2=region
    return {'original':[x1,y1,x2,y2],
            'rotate90cw':[1-y2,x1,1-y1,x2],'rotate180':[1-x2,1-y2,1-x1,1-y1],
            'rotate270cw':[y1,1-x2,y2,1-x1],'flip_horizontal':[1-x2,y1,1-x1,y2],
            'flip_vertical':[x1,1-y2,x2,1-y1]}[view]


def to_original_region(region,view):
    inverse={'original':'original','rotate90cw':'rotate270cw','rotate270cw':'rotate90cw',
             'rotate180':'rotate180','flip_horizontal':'flip_horizontal','flip_vertical':'flip_vertical'}
    return transform_region(region,inverse[view])


def belongs_to_target(region,target):
    if len(region)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in region):return False
    x1,y1,x2,y2=region; rx1,ry1,rx2,ry2=target['region']
    area=(x2-x1)*(y2-y1)
    if x2<=x1 or y2<=y1 or area<target.get('minAreaFraction',0)*(rx2-rx1)*(ry2-ry1):return False
    cx,cy=(x1+x2)/2,(y1+y2)/2
    intersection=max(0,min(x2,rx2)-max(x1,rx1))*max(0,min(y2,ry2)-max(y1,ry1))
    return rx1<=cx<=rx2 and ry1<=cy<=ry2 and intersection/area>=target.get('minInsideFraction',.8)


def select_labelled_boxes(image,targets,detect):
    """Keep original correct boxes; augment only unresolved targets, never relabel."""
    selected={}
    for view in ('original',)+FALLBACK_VIEWS:
        query=image if view=='original' else image.transpose(OPERATIONS[view])
        detections=detect(query)
        mapped=[{**d,'region':to_original_region(d['region'],view)} for d in detections]
        used=set()
        for index,target in enumerate(targets):
            if index in selected:continue
            candidates=[(i,d) for i,d in enumerate(mapped) if i not in used and
                        d.get('categoryID')==target['categoryID'] and belongs_to_target(d['region'],target)]
            if candidates:
                candidate_index,best=max(candidates,key=lambda item:item[1]['score'])
                used.add(candidate_index)
                selected[index]={**best,'sourceTransform':view,'labelSource':'provided_catalogue',
                                 'targetIndex':index,'articleIDs':target.get('articleIDs',[])}
        if len(selected)==len(targets):break
    return [selected[i] for i in sorted(selected)]

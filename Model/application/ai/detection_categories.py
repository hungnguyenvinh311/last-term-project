"""Stable catalogue categories for the detector's five prompts."""
DETECTION_LABELS=('a mobile phone','a laptop computer','a tablet computer','headphones','a smartwatch')
CATEGORY_NAMES={1:'Điện thoại',2:'Laptop',3:'Máy tính bảng',4:'Tai nghe',5:'Đồng hồ'}
ALIASES={'mobile phone':1,'smartphone':1,'phone':1,'laptop computer':2,'laptop':2,
         'tablet computer':3,'tablet':3,'headphone':4,'smartwatch':5}

def category_for_label(label):
    label=str(label or '').strip().lower()
    if label in DETECTION_LABELS:return DETECTION_LABELS.index(label)+1
    return ALIASES.get(label)

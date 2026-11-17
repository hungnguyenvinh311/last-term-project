"""Electronics criteria extraction; explicit deterministic adapter, not an LLM claim."""
import re
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.normalization import fold
from Model.application.errors import DomainError

CATEGORIES={1:['dien thoai','smartphone','iphone'],2:['laptop','macbook','may tinh xach tay'],
            3:['tablet','may tinh bang','ipad'],4:['tai nghe','headphone','earbud','airpod'],
            5:['dong ho','smartwatch','apple watch']}
BRANDS=['samsung','apple','xiaomi','honor','huawei','oppo','lenovo','asus','acer','dell','hp','msi','sony','jbl','anker','garmin','amazfit','nothing','coros','beats','shokz']

class IntentExtractorService:
    def extractCriteria(self,text):
        text=text.strip()
        if not text or len(text)>2000: raise DomainError('Nhập yêu cầu tìm kiếm từ 1 đến 2000 ký tự')
        t=fold(text);criteria=SearchCriteria(text=text)
        if t in {'xin chao','hello','hi','cam on','ban co khoe khong'}: raise DomainError('Hãy nhập nhu cầu tìm sản phẩm điện tử.')
        # "không dây" means wireless; it is a feature, not exclusion of "dây".
        negative=[m for m in re.finditer(r'(?:khong(?:\s+(?:lay|chon|muon|phai))?|tru|exclude)\s+([a-z0-9]+)',t)
                  if not (m.group(0)=='khong day')]
        criteria.excludedTerms=[m.group(1) for m in negative]
        positive=t
        for m in reversed(negative): positive=positive[:m.start()]+' '+positive[m.end():]
        for cid,terms in CATEGORIES.items():
            if any(term in positive for term in terms): criteria.categoryID=cid;break
        for brand in BRANDS:
            if re.search(r'\b'+brand+r'\b',positive): criteria.brand=brand;break
        if 'iphone' in positive or 'ipad' in positive or 'macbook' in positive or 'airpod' in positive or 'apple watch' in positive:
            criteria.brand='apple'
        # Budget expressions are independent of product-model numbers and GB.
        amount=r'(\d+(?:[.,]\d+)?)\s*(trieu|tr|m|k|nghin|ngan|vnd|dong)\b'
        for m in re.finditer(amount,positive):
            value=float(m.group(1).replace(',','.'))*({'trieu':1e6,'tr':1e6,'m':1e6,'k':1000,'nghin':1000,'ngan':1000}.get(m.group(2),1))
            prefix=positive[max(0,m.start()-24):m.start()]
            if re.search(r'(tren|tu|toi thieu|it nhat)\s*$',prefix): criteria.minPrice=value
            elif re.search(r'(duoi|den|toi da|khong qua|tam|khoang|ngan sach)\s*$',prefix): criteria.maxPrice=value
            else: criteria.maxPrice=value
        price_range=re.search(r'tu\s+(\d+(?:[.,]\d+)?)\s*(trieu|tr|m|k|nghin|ngan)?\s*(?:den|toi|-)\s*(\d+(?:[.,]\d+)?)\s*(trieu|tr|m|k|nghin|ngan)\b',positive)
        if price_range:
            first,first_unit,last,last_unit=price_range.groups()
            scales={'trieu':1e6,'tr':1e6,'m':1e6,'k':1000,'nghin':1000,'ngan':1000}
            criteria.minPrice=float(first.replace(',','.'))*scales[first_unit or last_unit]
            criteria.maxPrice=float(last.replace(',','.'))*scales[last_unit]
        if criteria.minPrice is not None and criteria.maxPrice is not None and criteria.minPrice>criteria.maxPrice: raise DomainError('Khoảng giá mâu thuẫn')
        ram=re.search(r'ram\s*(\d+)\s*(?:gb)?',positive) or re.search(r'(\d+)\s*gb\s*ram',positive)
        if ram: criteria.specs['ram']=int(ram.group(1))
        storage=re.search(r'(?:bo nho|o cung|rom|storage)\s*(\d+)\s*(?:gb)?',positive)
        if storage: criteria.specs['storage']=int(storage.group(1))
        fields={'ram':r'ram','storage':r'(?:bo nho|o cung|rom|storage)','battery':r'(?:pin|battery)','screen':r'(?:man hinh|screen)','camera':r'(?:camera sau|camera)'}
        for key,label in fields.items():
            match=re.search(label+r'\s*(it nhat|toi thieu|tu|tren|toi da|duoi)?\s*(\d+(?:[.,]\d+)?)\s*(gb|mah|inch(?:es)?|mp)\b',positive)
            if match:
                modifier,value,unit=match.groups()
                criteria.specs[key]={'value':float(value.replace(',','.')),'op':'min' if modifier in {'it nhat','toi thieu','tu','tren'} else ('max' if modifier in {'toi da','duoi'} else 'eq'),'unit':unit[:4] if unit.startswith('inch') else unit}
        for token in ['5g','oled','amoled','android','ios','gaming','chong on','bluetooth','usb-c']:
            if token in positive: criteria.requiredTerms.append(token)
        # Explicit model names are required evidence, not a soft visual preference.
        model=re.search(r'\b(iphone\s+\d+(?:\s+pro)?(?:\s+max)?|galaxy\s+[as]\d+(?:\s+ultra)?|rtx\s*\d+|macbook\s+(?:air|pro))\b',positive)
        if model: criteria.requiredTerms.append(model.group(1))
        for term in ['hoc tap','van phong','chup anh','pin lau','nhe','the thao']:
            if term in positive: criteria.preferredTerms.append(term)
        from Model.application.ai.colors import apply_colors
        return apply_colors(criteria,text)

def canonical_query(criteria):
    categories={1:'smartphone mobile phone',2:'laptop computer',3:'tablet computer',4:'headphones earbuds',5:'smartwatch wrist watch'}
    translations={'hoc tap':'study','van phong':'office','chup anh':'camera photography','pin lau':'long battery','nhe':'lightweight','the thao':'sports','chong on':'noise cancelling'}
    parts=[categories.get(criteria.categoryID,''),criteria.brand or '']
    parts += [(t[6:] if t.startswith('color:') else translations.get(t,t)) for t in criteria.requiredTerms+criteria.preferredTerms]
    parts += [f'{k} {v["value"]} {v["unit"]}' if isinstance(v,dict) else f'{k} {v} GB' for k,v in criteria.specs.items()]
    return ' '.join(p for p in parts if p) or criteria.text

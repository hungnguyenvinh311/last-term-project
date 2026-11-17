import re
import unicodedata
from Model.application.config.brands import brand_key

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower().replace('đ','d')) if not unicodedata.combining(c))

def product_text(p):
    specs=p.get('technicalSpecs') or {}
    searchable={k:v for k,v in specs.items() if not any(x in fold(k) for x in ('so luong kha dung','stock quantity','inventory quantity'))} if isinstance(specs,dict) else specs
    return fold(' '.join(str(p.get(k) or '') for k in ('productName','brand','description'))+' '+str(searchable))

def model_key(product):
    text=fold(product['productName']).split('|')[0]
    for phrase in ['dong ho thong minh','dong ho','bluetooth','chinh hang','day cao su','silicone']:
        text=text.replace(phrase,' ')
    return re.sub(r'[^a-z0-9]','',text)

def contains(text, term):
    return bool(re.search(r'(?<!\w)'+re.escape(fold(term))+r'(?!\w)', fold(text)))

def matches(p, criteria):
    if not p.get('isActive'): return False
    if criteria.categoryID and p['categoryID'] != criteria.categoryID: return False
    if criteria.brand and brand_key(p.get('brand')) != brand_key(criteria.brand): return False
    if criteria.minPrice is not None and (p['price'] is None or float(p['price']) < criteria.minPrice): return False
    if criteria.maxPrice is not None and (p['price'] is None or float(p['price']) > criteria.maxPrice): return False
    text=product_text(p)
    specs={k:v for k,v in (p.get('technicalSpecs') or {}).items() if not any(x in fold(k) for x in ('so luong kha dung','stock quantity','inventory quantity'))}
    evidence=fold(p.get('productName','')+' '+' '.join(str(v) for v in specs.values()))
    color_evidence=fold(p.get('productName','')+' '+' '.join(str(v) for k,v in specs.items() if 'mau' in fold(k) or 'color' in fold(k) or 'colour' in fold(k)))
    for term in criteria.requiredTerms:
        if term.startswith('color:'):
            from Model.application.ai.colors import color_matches
            if not color_matches(color_evidence,term): return False
        elif term=='chong on':
            support=any('chong on' in fold(k) and fold(v).strip() in {'co','yes','anc','active noise cancelling'} for k,v in (p.get('technicalSpecs') or {}).items())
            if not support and not any(contains(evidence,t) for t in ['chong on','anc','noise cancelling']): return False
        elif not contains(evidence,term): return False
    from Model.application.ai.colors import color_matches
    if any(color_matches(color_evidence,t) if t.startswith('color:') else contains(text,t) for t in criteria.excludedTerms): return False
    specs=p.get('technicalSpecs') or {}
    for key, expected in criteria.specs.items():
        keys={'ram':['ram'],'storage':['bo nho trong','dung luong o cung','storage','rom'],'battery':['pin','battery'],'screen':['kich thuoc man hinh','screen size'],'camera':['camera sau','rear camera']}
        values=[str(v) for k,v in specs.items() if any(term in fold(k) for term in keys.get(key,[key]))]
        condition=expected if isinstance(expected,dict) else {'value':expected,'op':'eq','unit':'gb'}
        unit=condition['unit'];numbers=[]
        for value in values:
            for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*'+re.escape(unit),fold(value)):
                numbers.append(float(m.group(1).replace(',','.')))
        target=condition['value'];op=condition['op']
        if not any({'eq':n==target,'min':n>=target,'max':n<=target}[op] for n in numbers): return False
    return True

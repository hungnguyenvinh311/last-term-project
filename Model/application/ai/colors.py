"""Explicit colour constraints, backed by catalogue evidence rather than image guesses."""
import re
from Model.application.normalization import fold,contains
COLORS={
 'black':('den','black'), 'white':('trang','white'), 'red':('do','red'),
 'blue':('xanh duong','xanh lam','blue'), 'green':('xanh la','green'),
 'yellow':('vang','yellow'), 'pink':('hong','pink'), 'purple':('tim','purple'),
 'silver':('bac','silver'), 'gray':('xam','ghi','gray','grey'),
 'orange':('cam','orange'),
 'brown':('nau','brown'),
}
def color_terms(text):
    value=fold(text); result=[]
    # Vietnamese single-word colours require a colour cue to avoid "den 10 trieu".
    for color,aliases in COLORS.items():
        if any(contains(value,a) for a in aliases if len(a.split())>1 or a==color) or any(contains(value,'mau '+a) for a in aliases):
            result.append('color:'+color)
    return result

def color_matches(evidence,term):
    return any(contains(evidence,a) for a in COLORS.get(term[6:],()))

def apply_colors(criteria,text):
    negative=[]
    positive=fold(text)
    for match in list(re.finditer(r'(?:khong|tru|exclude|not)\s+(?:mau\s+)?([a-z]+(?:\s+(?:duong|lam|la))?)',positive))[::-1]:
        negative+=color_terms('mau '+match.group(1))
        positive=positive[:match.start()]+' '+positive[match.end():]
    if negative:
        aliases={a for values in COLORS.values() for a in values}
        criteria.excludedTerms=[t for t in criteria.excludedTerms if t!='mau' and t not in aliases]
    criteria.excludedTerms=list(dict.fromkeys(criteria.excludedTerms+negative))
    terms=color_terms(positive)
    if terms:
        colour_phrases={phrase for aliases in COLORS.values() for a in aliases for phrase in (a,'mau '+a)}
        criteria.requiredTerms=list(dict.fromkeys([t for t in criteria.requiredTerms if fold(t).strip() not in colour_phrases]+terms))
    return criteria

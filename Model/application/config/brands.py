"""Canonical brand labels; promotional suffixes do not identify new brands."""
import re
import unicodedata

def canonical_brand(value):
    if value is None:return None
    value=unicodedata.normalize('NFC',str(value)).strip()
    value=re.sub(r'(?:[\s|,\-]+)(?:chính\s+hãng|chinh\s+hang)\s*$','',value,flags=re.I).strip()
    aliases={'samsung':'Samsung','apple':'Apple','beats':'Beats','xiaomi':'Xiaomi','honor':'HONOR',
             'asus':'ASUS','hp':'HP','msi':'MSI','oppo':'OPPO','jbl':'JBL'}
    return aliases.get(value.casefold(),value) or None

def brand_key(value):
    return (canonical_brand(value) or '').casefold()

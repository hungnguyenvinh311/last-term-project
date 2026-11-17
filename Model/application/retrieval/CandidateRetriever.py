import re
import os
from collections import Counter
import numpy as np
from Model.application.normalization import fold,product_text
from Model.application.retrieval.representations import metadata,valid

def cosine(a,b):
    if a is None or b is None: return None
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all(): return None
    norm=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/norm) if norm>0 else None

class CandidateRetriever:
    def __init__(self,products,embedder): self.products,self.embedder=products,embedder
    def retrieveForQuery(self,criteria,vector=None,mode='text',textVector=None):
        candidates=self.products.findByRepresentation(criteria);manifest=metadata();result=[]
        tokens=[t for t in re.findall(r'[a-z0-9]+',fold(criteria.text)) if len(t)>2 and t not in {'tim','toi','cho','mua','muon','mot','san','pham','can','voi'}]
        structured=bool(criteria.categoryID or criteria.brand or criteria.requiredTerms or criteria.specs or criteria.maxPrice is not None or criteria.minPrice is not None or criteria.excludedTerms)
        for p in candidates:
            # A selected object's category is a hard boundary, never a soft score.
            if criteria.categoryID and p['categoryID']!=criteria.categoryID:continue
            text=product_text(p);lexical=sum(t in text for t in tokens)/max(1,len(tokens))
            similarity=None
            if vector is not None and valid(p,manifest,self.embedder.identity):
                vectors=[p.get('imageEmbedding')] if mode=='image' else [p.get('textEmbedding'),p.get('imageEmbedding')]
                scores=[cosine(vector,v) for v in vectors];scores=[s for s in scores if s is not None]
                if scores: similarity=max(scores)
            if mode=='image' and similarity is None: continue
            if mode=='image' and similarity<float(os.getenv('APP_IMAGE_MIN_SIMILARITY','0.25')): continue
            if not structured and lexical==0 and (similarity is None or similarity<0.2): continue
            text_similarity=cosine(textVector,p.get('textEmbedding')) if textVector is not None and valid(p,manifest,self.embedder.identity) else None
            result.append({**p,'similarity':similarity,'textSimilarity':text_similarity,'lexical':lexical,
                           'searchMode':'image_text' if textVector is not None else mode})
        if mode=='image' and result and not criteria.categoryID:
            nearest=sorted(result,key=lambda p:-p['similarity'])[:5]
            category,votes=Counter(p['categoryID'] for p in nearest).most_common(1)[0]
            if votes/len(nearest)>=0.6: result=[p for p in result if p['categoryID']==category]
        return result
    def retrieveAlternatives(self,source): return self.products.findAlternatives(source)
    def findFallbackAlternatives(self,source): return self.products.findAlternatives(source)

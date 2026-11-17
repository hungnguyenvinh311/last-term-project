from Model.application.retrieval.CandidateRetriever import cosine
from Model.application.retrieval.representations import metadata,valid

class SoftReranker:
    def __init__(self,identity,search_weights=None): self.identity,self.search_weights=identity,search_weights or {}
    def rankForQuery(self,candidates,criteria,limit=12,weights=None):
        from Model.application.retrieval.RankingEvaluation import weighted_score
        scored=[]
        for p in candidates:
            mode=p.get('searchMode','image_text' if p.get('textSimilarity') is not None else 'single')
            chosen=weights if weights is not None else self.search_weights.get(mode,((.6,.2,.2) if p.get('textSimilarity') is not None else (.8,0,.2)))
            score=weighted_score(p,chosen)
            scored.append({**p,'score':float(score),'matchDetails':{'metric':'cosine','embedding':p.get('similarity'),'text':p.get('textSimilarity'),'keyword':p.get('lexical',0),'rankScore':float(score),'mode':mode,'weights':list(chosen)}})
        return self._ordered(scored,limit)
    def rankForProduct(self,candidates,source,limit=8):
        manifest=metadata();scored=[]
        if not valid(source,manifest,self.identity): return []
        for p in candidates:
            if not valid(p,manifest,self.identity): continue
            scores=[cosine(source.get(k),p.get(k)) for k in ('imageEmbedding','textEmbedding')]
            scores=[s for s in scores if s is not None]
            if not scores: continue
            # Appearance is only one relevance signal; price/brand are soft preferences.
            price_similarity=1-abs(float(p['price'])-float(source['price']))/max(float(p['price']),float(source['price']),1)
            score=sum(scores)/len(scores)*0.75+price_similarity*0.2+(0.05 if p.get('brand')==source.get('brand') else 0)
            scored.append({**p,'score':float(score),'fallback':False})
        return self._ordered(scored,limit)
    @staticmethod
    def _ordered(rows,limit):
        rows=sorted(rows,key=lambda p:(-p['score'],p['articleID']))[:limit]
        return [{**p,'rank':i} for i,p in enumerate(rows,1)]

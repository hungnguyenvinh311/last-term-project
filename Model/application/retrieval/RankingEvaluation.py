"""Offline evaluation. Never selects parameters using held-out test relevance."""
import math
from statistics import mean

def weighted_score(row,weights):
    if len(weights)!=3 or any(not math.isfinite(w) or w<0 for w in weights) or not math.isclose(sum(weights),1,abs_tol=1e-8):
        raise ValueError('Three finite nonnegative weights summing to one are required')
    values=(row.get('similarity'),row.get('textSimilarity'),row.get('lexical'))
    return sum(w*(float(v) if v is not None else 0) for w,v in zip(weights,values))

def grid(kind,steps=20):
    if not isinstance(steps,int) or steps<1:raise ValueError('Positive integer grid steps required')
    if kind=='image': return [(1.,0.,0.)] # No textual signal exists to tune.
    if kind=='text':return [(i/steps,0.,(steps-i)/steps) for i in range(steps+1)]
    if kind=='image_text':return [(i/steps,j/steps,(steps-i-j)/steps) for i in range(steps+1) for j in range(steps-i+1)]
    raise ValueError('Unsupported search kind')

def metrics(rows,truth,weights,k):
    if k<1:raise ValueError('K must be positive')
    truth=set(truth)
    if len({r['articleID'] for r in rows})!=len(rows):raise ValueError('Duplicate candidate IDs')
    ranked=sorted(rows,key=lambda r:(-weighted_score(r,weights),r['articleID']))
    ids=[r['articleID'] for r in ranked[:k]]
    hits=[int(i in truth) for i in ids]
    dcg=sum(hit/math.log2(rank+2) for rank,hit in enumerate(hits))
    ideal=sum(1/math.log2(rank+2) for rank in range(min(k,len(truth))))
    no_answer=float(not rows) if not truth else None
    return {'ndcgAtK':dcg/ideal if ideal else no_answer,
            'recallAtK':sum(hits)/len(truth) if truth else None,
            'precisionAtK':sum(hits)/k,
            'mrrAtK':next((1/(i+1) for i,h in enumerate(hits) if h),0.) if truth else None,
            'hitAt1':float(bool(hits and hits[0])) if truth else None,
            'candidateRecall':len({r['articleID'] for r in rows}&truth)/len(truth) if truth else None,
            'noAnswerCorrect':no_answer,'returned':ids}

def aggregate(cases,weights,k):
    values=[metrics(c['candidates'],c['relevantArticleIDs'],weights,k) for c in cases]
    if not values:raise ValueError('Nonempty evaluation split required')
    keys=[key for key in values[0] if key!='returned']
    return {key:mean(v[key] for v in values if v[key] is not None) if any(v[key] is not None for v in values) else None for key in keys}

def validate_cases(cases,reviewed=True):
    if not cases or len({c['caseID'] for c in cases})!=len(cases):raise ValueError('Nonempty unique case IDs required')
    groups={}
    for c in cases:
        if reviewed and c.get('reviewed') is not True:raise ValueError('Human review is required; exploratory mode must be explicit')
        if c['kind'] not in {'text','image','image_text'} or c['split'] not in {'validation','test'}:raise ValueError('Invalid kind/split')
        if not c.get('groupID') or not isinstance(c.get('relevantArticleIDs'),list):raise ValueError('Explicit group and relevance labels required')
        if any(not isinstance(v,int) or isinstance(v,bool) for v in c['relevantArticleIDs']):raise ValueError('Integer product IDs required')
        group=c['groupID']
        if group in groups and groups[group]!=c['split']:raise ValueError('Product-group leakage between validation and test')
        groups[group]=c['split']

def tune(cases,steps=20,k=5,reviewed=True):
    validate_cases(cases,reviewed)
    result={}
    for kind in sorted({c['kind'] for c in cases}):
        validation=[c for c in cases if c['kind']==kind and c['split']=='validation']
        test=[c for c in cases if c['kind']==kind and c['split']=='test']
        baseline=(.6,.2,.2) if kind=='image_text' else (.8,0,.2)
        trials=[]
        for weights in grid(kind,steps):
            score=aggregate(validation,weights,k)
            distance=sum((a-b)**2 for a,b in zip(weights,baseline))
            trials.append((score['ndcgAtK'],score['recallAtK'] or 0,score['mrrAtK'] or 0,-distance,weights,score))
        best=max(trials,key=lambda t:t[:4])
        tied=sum(all(math.isclose(t[i],best[i],abs_tol=1e-10) for i in range(3)) for t in trials)
        weights=best[4]
        result[kind]={'weights':dict(zip(('cosine','text','keyword'),weights)),
                      'trials':len(trials),'equallyGoodValidationSettings':tied,
                      'validationCases':len(validation),'testCases':len(test),
                      'baselineValidation':aggregate(validation,baseline,k),'selectedValidation':best[5],
                      'baselineTest':aggregate(test,baseline,k),'selectedTest':aggregate(test,weights,k),
                      'selection':'Validation NDCG@K, Recall@K, MRR@K; ties prefer existing weights. Test labels are never used for selection.'}
    return result

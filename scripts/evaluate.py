"""Evaluate reviewed labels; never treats synthetic/unreviewed labels as ground truth."""
import sys,json,argparse,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from bootstrap import create_app
from Model.application.ai.IntentExtractorService import canonical_query
from Model.application.dto.SearchCriteria import SearchCriteria
from crawler.storage.files import save_json
from Model.application.errors import AIUnavailable

def evaluate(file,k):
    cases=json.loads(Path(file).read_text(encoding='utf-8'))
    if not cases or k<1: raise ValueError('Provide nonempty reviewed cases and K >= 1')
    if any(not c.get('reviewed') for c in cases): raise ValueError('All relevance labels must be reviewed before evaluation')
    services=create_app().state.services;s=services['search'];output=[]
    for c in cases:
        kind=c['kind'];start=time.perf_counter()
        if kind=='recommendation': rows=services['recommendation'].recommendForProduct(c['sourceArticleID'],k)['products']
        else:
            criteria=s.intent.extractCriteria(c['text']) if kind in {'text','voice'} else SearchCriteria()
            if kind=='image':
                image=s.media.validateImage((ROOT/c['image']).read_bytes())
                if c.get('region'):image=s.detector.cropRegion(image,c['region'])
                vector=s.embedder.encodeImage(image)
            else: vector=s.embedder.encodeText(canonical_query(criteria))
            rows=s.ranking.rankForQuery(s.retriever.retrieveForQuery(criteria,vector,'image' if kind=='image' else 'text'),criteria,k)
        truth=set(c['relevantArticleIDs']);returned={p['articleID'] for p in rows[:k]};hits=len(truth & returned)
        output.append({'caseID':c['caseID'],'kind':kind,'recallAtK':hits/len(truth) if truth else None,
                       'precisionAtK':hits/k,'noAnswerCorrect':not returned if not truth else None,
                       'returned':sorted(returned),'seconds':time.perf_counter()-start})
    save_json(ROOT/'data/evaluation/results.json',{'K':k,'shortListPolicy':'Precision denominator is K even for shorter lists','voicePolicy':'Provided reviewed transcript; audio transcription quality must be measured separately','cases':output})
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('cases');parser.add_argument('--k',type=int,default=5);a=parser.parse_args()
    print(json.dumps(evaluate(a.cases,a.k),indent=2))

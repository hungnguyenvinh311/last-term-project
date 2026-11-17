"""Offline feature extraction + validation grid; never changes live ranking weights."""
import sys,json,argparse,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from bootstrap import create_app
from crawler.storage.files import save_json
from Model.application.ai.IntentExtractorService import IntentExtractorService,canonical_query
from Model.application.dto.SearchCriteria import SearchCriteria
from Model.application.retrieval.RankingEvaluation import tune,validate_cases,metrics
from Model.application.retrieval.representations import source_hash

def run(cases_file,output,exploratory=False,k=5,steps=20):
    path=Path(cases_file);cases=json.loads(path.read_text(encoding='utf-8'))
    validate_cases(cases,reviewed=not exploratory)
    app=create_app(overrides={'intent':IntentExtractorService()})
    services=app.state.services;s=services['search'];products=services['products'].findActive()
    ids={p['articleID'] for p in products}
    for c in cases:
        if set(c['relevantArticleIDs'])-ids:raise ValueError('Relevance contains unknown/inactive product IDs')
    fingerprint=hashlib.sha256(json.dumps([(p['articleID'],str(p['price']),p.get('isActive'),source_hash(p)) for p in products],sort_keys=True).encode()).hexdigest()
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    features=[];started=time.perf_counter()
    for index,c in enumerate(cases):
        kind=c['kind'];criteria=s._criteria(c['text']) if c.get('text','').strip() else SearchCriteria(text='Image search')
        criteria=s._filters(criteria,c.get('brand'),c.get('categoryID'))
        if kind=='text':
            vector=s._text_vector(canonical_query(criteria));extra=None;mode='text'
        else:
            image_path=(ROOT/c['image']).resolve()
            image_path.relative_to(ROOT.resolve())
            image=s.media.validateImage(image_path.read_bytes())
            if c.get('region'):image=s.detector.cropRegion(image,c['region'])
            vector=s.embedder.encodeImage(image);mode='image'
            extra=s._text_vector(canonical_query(criteria)) if kind=='image_text' else None
        candidates=s.retriever.retrieveForQuery(criteria,vector,mode,textVector=extra)
        rows=[{key:p.get(key) for key in ('articleID','similarity','textSimilarity','lexical')} for p in candidates]
        features.append({**c,'candidates':rows,'parsedCriteria':criteria.to_dict()})
        if (index+1)%10==0:print(f'Extracted {index+1}/{len(cases)} cases',flush=True)
    save_json(output/'features.json',features)
    selected=tune(features,steps,k,reviewed=not exploratory)
    rankings=[]
    for c in features:
        w=selected[c['kind']]['weights'];weights=(w['cosine'],w['text'],w['keyword'])
        rankings.append({'caseID':c['caseID'],'kind':c['kind'],'split':c['split'],'criteria':c['parsedCriteria'],
                         'relevantArticleIDs':c['relevantArticleIDs'],**metrics(c['candidates'],c['relevantArticleIDs'],weights,k)})
    report={'status':'EXPLORATORY_UNREVIEWED_NOT_FOR_DEPLOYMENT' if exploratory else 'REVIEWED_OFFLINE_EVALUATION',
            'K':k,'gridStep':1/steps,'caseFileSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'catalogueFingerprint':fingerprint,'encoder':s.embedder.identity,'cases':len(cases),
            'selected':selected,'seconds':time.perf_counter()-started,'liveConfigurationChanged':False,
            'limits':['Catalogue self-images/title queries are optimistic diagnostics, not independent customer queries.',
                      'Binary labels must include all relevant products; suggested labels are not exhaustive ground truth.',
                      'Candidate thresholds/category voting are fixed; weights cannot recover products filtered out earlier.',
                      'Rule parser used consistently; Gemini intent and voice transcription quality are not evaluated.',
                      'No colour quality claim without reviewed colour evidence and colour-specific queries.']}
    save_json(output/'report.json',report);save_json(output/'rankings.json',rankings)
    lines=['# Search ranking grid search','',report['status'],'',f'{len(cases)} queries · K={k} · grid step={1/steps} · live weights unchanged.','',
           '| Mode | Trials | Tied best settings | Selected cosine/text/keyword | Validation NDCG baseline → selected | Test NDCG baseline → selected |','|---|---:|---:|---|---|---|']
    for kind,r in selected.items():
        w=r['weights'];lines.append(f'| {kind} | {r["trials"]} | {r["equallyGoodValidationSettings"]} | {w["cosine"]:.2f}/{w["text"]:.2f}/{w["keyword"]:.2f} | {r["baselineValidation"]["ndcgAtK"]:.4f} → {r["selectedValidation"]["ndcgAtK"]:.4f} | {r["baselineTest"]["ndcgAtK"]:.4f} → {r["selectedTest"]["ndcgAtK"]:.4f} |')
    lines+=['','## Limits','']+['- '+v for v in report['limits']]
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Grid search complete; no live weights or database records changed.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases');p.add_argument('--output',required=True);p.add_argument('--exploratory',action='store_true');p.add_argument('--k',type=int,default=5);p.add_argument('--steps',type=int,default=20)
    a=p.parse_args();run(a.cases,a.output,a.exploratory,a.k,a.steps)

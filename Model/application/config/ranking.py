import json
from Model.application.config.settings import ROOT
from Model.application.retrieval.RankingEvaluation import weighted_score

def load_search_weights(path=None):
    data=json.loads((path or ROOT/'Model/application/config/search_ranking.json').read_text(encoding='utf-8'))
    result={}
    for mode in ('text','image','image_text'):
        weights=tuple(data[mode]);weighted_score({},weights)
        if mode in ('text','image') and weights[1]!=0:raise ValueError('Single-modality ranking has no extra text signal')
        if mode=='image' and weights!=(1,0,0):raise ValueError('Image-only search uses only image cosine')
        result[mode]=weights
    return result

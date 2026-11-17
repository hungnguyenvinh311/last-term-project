from copy import deepcopy
from threading import RLock
from time import monotonic
import os
from Model.application.dto.SearchCriteria import SearchCriteria

class SearchSessionService:
    def __init__(self,ttl=None): self.ttl=ttl if ttl is not None else int(os.getenv('APP_CONTEXT_SECONDS','1800'));self.items={};self.lock=RLock()
    def getOrCreate(self,key):
        with self.lock:
            now=monotonic()
            self.items={k:v for k,v in self.items.items() if now-v['time']<self.ttl}
            if key not in self.items:
                if len(self.items)>=1000: self.items.pop(next(iter(self.items)))
                self.items[key]={'criteria':SearchCriteria(),'results':[],'time':now}
            self.items[key]['time']=now
            return deepcopy(self.items[key])
    def mergeCriteria(self,key,criteria,reset=False):
        with self.lock:
            old=self.getOrCreate(key)['criteria']
            if reset or (criteria.categoryID and old.categoryID and criteria.categoryID!=old.categoryID): old=SearchCriteria()
            for field in ('categoryID','brand','minPrice','maxPrice'):
                value=getattr(criteria,field)
                if value is not None: setattr(old,field,value)
            old.text=criteria.text
            old.intentProvider=criteria.intentProvider
            old.intentWarning=criteria.intentWarning
            if any(t.startswith('color:') for t in criteria.requiredTerms): old.requiredTerms=[t for t in old.requiredTerms if not t.startswith('color:')]
            old.requiredTerms=list(dict.fromkeys(old.requiredTerms+criteria.requiredTerms))
            old.excludedTerms=list(dict.fromkeys(old.excludedTerms+criteria.excludedTerms))
            old.preferredTerms=list(dict.fromkeys(old.preferredTerms+criteria.preferredTerms))
            old.specs.update(criteria.specs)
            self.items[key]['criteria']=deepcopy(old)
            return old
    def rememberResults(self,key,results):
        with self.lock:
            self.getOrCreate(key);self.items[key]['results']=[p['articleID'] for p in results]

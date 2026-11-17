"""Invalidate derived labels without changing source photos or crawl snapshots."""
import json
from threading import RLock
from Model.application.config.settings import ROOT


class CatalogueArtifacts:
    def __init__(self,root=ROOT): self.root=root;self.lock=RLock()

    def invalidateLabels(self,articleID):
        path=self.root/'data/detection_labels/manifest.json'
        with self.lock:
            if not path.is_file(): return
            doc=json.loads(path.read_text(encoding='utf-8'))
            # Remove a whole composite when any of its supplied identities changed.
            images={k:v for k,v in doc['images'].items() if not any(articleID in t['articleIDs'] for t in v['targets'])}
            if len(images)==len(doc['images']): return
            backup=path.with_name('manifest.before_catalogue_edits.json')
            if not backup.exists(): backup.write_bytes(path.read_bytes())
            doc['images']=images
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(path)

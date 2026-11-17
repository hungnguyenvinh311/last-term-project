"""Build the explicitly provided label registry for catalogue photos and demo pairs."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT
from PIL import Image
from crawler.storage.files import save_json
from Model.application.ai.detection_transforms import pixel_fingerprint


def main():
    from DAO.application.dao.connection import Database
    from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
    catalog=ProductDAOImpl(Database()).findActive()
    source_catalog=json.loads((ROOT/'data/retailer_catalog/products.json').read_text(encoding='utf-8'))
    original={p['articleID']:p for p in source_catalog}
    # Reuse the already recorded coarse product regions as supplied annotations.
    annotated=json.loads((ROOT/'data/screen_confusion_tests/report.json').read_text(encoding='utf-8'))
    rois={r['articleID']:r['traits']['coarseProductROI'] for r in annotated['cases']}
    images={}
    for p in catalog:
        if not p.get('isActive'):continue
        if not p.get('imagePath') or not (ROOT/p['imagePath']).is_file(): continue
        with Image.open(ROOT/p['imagePath']) as image:key=pixel_fingerprint(image)
        target={'articleIDs':[p['articleID']],'categoryID':p['categoryID'],
                'region':rois.get(p['articleID'],[.02,.02,.98,.98]) if p['articleID'] in original and p['categoryID']==original[p['articleID']]['categoryID'] and p['imagePath']==original[p['articleID']]['imagePath'] else [.02,.02,.98,.98],
                'minInsideFraction':.7,'minAreaFraction':.05}
        if key in images:
            existing=images[key]['targets'][0]
            if existing['categoryID']!=target['categoryID']:raise ValueError('Conflicting labels for identical pixels')
            existing['articleIDs'].append(p['articleID'])
        else:images[key]={'imagePath':p['imagePath'],'kind':'catalogue','targets':[target]}
    pairs=json.loads((ROOT/'data/pairwise_search_tests/report.json').read_text(encoding='utf-8'))
    for pair in pairs['pairs']:
        live={p['articleID']:p for p in catalog}
        if any(t['articleID'] not in live or t['articleID'] not in original or
               live[t['articleID']]['categoryID']!=t['categoryID'] or
               live[t['articleID']]['imagePath']!=original[t['articleID']]['imagePath'] for t in pair['targets']): continue
        path=ROOT/'data/pairwise_search_tests'/pair['queryImage']
        with Image.open(path) as image:key=pixel_fingerprint(image)
        if key in images:raise ValueError('Unexpected duplicate composite')
        images[key]={'imagePath':str(path.relative_to(ROOT)),'kind':'composite','pairID':pair['pairID'],
                     'targets':[{'articleIDs':[t['articleID']],'categoryID':t['categoryID'],
                                 'region':t['panelRegion'],'minInsideFraction':.8,'minAreaFraction':0} for t in pair['targets']]}
    manifest={'version':1,'policy':'Explicit supplied catalogue labels; exact decoded RGB pixel match only.',
              'sources':['active Products in APP_DATABASE','data/pairwise_search_tests/report.json',
                         'data/screen_confusion_tests/report.json (coarse ROIs only)'],
              'images':images}
    save_json(ROOT/'data/detection_labels/manifest.json',manifest)
    print(f'Prepared {len(images)} distinct source images from {len(catalog)} catalogue rows and 10 composites.')


if __name__=='__main__':main()

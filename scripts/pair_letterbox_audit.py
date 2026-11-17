"""Input-geometry ablation only; never changes the live detector/preprocessor."""
import sys,json,time,hashlib,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageOps
from Model.application.config.settings import ROOT
from crawler.storage.files import save_json
from Model.application.ai.ObjectDetectorService import ObjectDetectorService
from scripts.pairwise_image_search import detection_for_target,draw_detections

def pad_square(image):
    side=max(image.size);left=(side-image.width)//2;top=(side-image.height)//2
    padded=Image.new('RGB',(side,side),'white');padded.paste(image,(left,top))
    return padded,(left,top)

def remap_region(region,original_size,padded_size,offset):
    w,h=original_size;pw,ph=padded_size;left,top=offset
    return [(region[0]*w+left)/pw,(region[1]*h+top)/ph,(region[2]*w+left)/pw,(region[3]*h+top)/ph]

def main():
    source=ROOT/'data/pairwise_search_tests'
    original=json.loads((source/'report.json').read_text(encoding='utf-8'))
    out=ROOT/'data/screen_confusion_tests/pair_letterbox';out.mkdir(exist_ok=False)
    (out/'images').mkdir();(out/'boxes').mkdir()
    os.environ.setdefault('HF_HUB_OFFLINE','1');detector=ObjectDetectorService();cases=[];start=time.perf_counter()
    for i,pair in enumerate(original['pairs'],1):
        with Image.open(source/pair['queryImage']) as photo:image=photo.convert('RGB')
        square,offset=pad_square(image);square.save(out/'images'/f'{pair["pairID"]}.png')
        row={'pairID':pair['pairID'],'originalSize':list(image.size),'paddedSize':list(square.size),'offset':list(offset)}
        for variant,query in [('baseline',image),('letterbox',square)]:
            detections=detector.detectProducts(query);targets=[]
            for t in pair['targets']:
                target=dict(t)
                if variant=='letterbox':target['panelRegion']=remap_region(t['panelRegion'],image.size,square.size,offset)
                top,correct=detection_for_target(detections,target)
                targets.append({'articleID':t['articleID'],'expectedCategoryID':t['categoryID'],
                                'strongest':top,'isCorrect':bool(top and top['categoryID']==t['categoryID']),
                                'isPhone':bool(top and top['categoryID']==1),'correctLabelAvailable':correct is not None})
            row[variant]={'detections':detections,'targets':targets}
            draw_detections(query,detections,[]).save(out/'boxes'/f'{pair["pairID"]}_{variant}.png')
        cases.append(row);save_json(out/'partial_results.json',cases)
        print(f'{i}/10 {pair["pairID"]}: baseline correct={sum(t["isCorrect"] for t in row["baseline"]["targets"])}, letterbox correct={sum(t["isCorrect"] for t in row["letterbox"]["targets"])}',flush=True)
    summary={variant:{'targets':20,'correctTop1':sum(t['isCorrect'] for r in cases for t in r[variant]['targets']),
                      'falsePhoneTop1':sum(t['isPhone'] and t['expectedCategoryID']!=1 for r in cases for t in r[variant]['targets']),
                      'correctLabelAvailable':sum(t['correctLabelAvailable'] for r in cases for t in r[variant]['targets'])} for variant in ('baseline','letterbox')}
    report={'summary':summary,'cases':cases,'seconds':time.perf_counter()-start,
            'processorResize':detector.processor.image_processor.size,
            'model':os.getenv('APP_DETECTOR_MODEL','google/owlvit-base-patch32'),'threshold':.15,
            'limits':'Same five representatives and synthetic layouts; padding changes object scale/context as well as avoiding aspect distortion. No production changes or independent accuracy claim.'}
    save_json(out/'report.json',report)
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()

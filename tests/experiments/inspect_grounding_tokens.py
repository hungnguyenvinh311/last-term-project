"""Compare adapter class decoding against the model's official phrase decoding."""
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Model.application.config.settings import ROOT
from PIL import Image
import torch
from Model.application.ai.CandidateObjectDetectorService import CandidateObjectDetectorService
from Model.application.ai.detection_categories import DETECTION_LABELS

torch.set_num_threads(4)
detector=CandidateObjectDetectorService('grounding_dino',padding=False,device='cuda');detector.load()
cases=json.loads((ROOT/'data/screen_confusion_tests/report.json').read_text(encoding='utf-8'))['cases']
row=next(r for r in cases if r['articleID']==81)
image=Image.open(ROOT/row['imagePath']).convert('RGB')
inputs=detector.processor(images=image,text='. '.join(DETECTION_LABELS)+'.',return_tensors='pt').to('cuda')
print('Tokens:',detector.processor.tokenizer.convert_ids_to_tokens(inputs.input_ids[0].tolist()),flush=True)
with torch.inference_mode(): outputs=detector.model(**inputs)
results=detector.processor.post_process_grounded_object_detection(outputs,inputs.input_ids,box_threshold=.4,text_threshold=.3,target_sizes=[image.size[::-1]])
for result in results:
    print('Official:',[(str(label),float(score)) for label,score in zip(result['text_labels'] if 'text_labels' in result else result['labels'],result['scores'])],flush=True)
    top=outputs.logits[0].sigmoid().max(-1).values.argsort(descending=True)[:5]
    for idx in top:
        vals=outputs.logits[0,idx].sigmoid()
        ids=inputs.input_ids[0].tolist()
        print('Scores:',[(token,round(float(vals[i]),3)) for i,token in enumerate(detector.processor.tokenizer.convert_ids_to_tokens(ids))],flush=True)
print('Adapter:',detector.detectProducts(image),flush=True)

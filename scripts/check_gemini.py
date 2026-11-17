"""Read-only model check by default; --text explicitly makes one generation call."""
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from Model.application.ai.GeminiClient import GeminiClient
from Model.application.ai.GeminiIntentExtractorService import GeminiIntentExtractorService
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.errors import AIUnavailable,DomainError

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--text',help='One real text extraction request; uses Gemini quota')
    args=parser.parse_args();provider=GeminiClient()
    try:
        for task in ['transcription','intent']:
            key,model=provider.configuration(task)
            if not key: raise AIUnavailable('Chưa điền APP_GEMINI_API_KEY trong .env.app')
            with httpx.Client(timeout=20) as client:
                r=client.get('https://generativelanguage.googleapis.com/v1beta/models/'+model,headers={'x-goog-api-key':key})
            if r.status_code!=200:
                print(json.dumps({'task':task,'model':model,'httpStatus':r.status_code,'ok':False}));return 1
            methods=r.json().get('supportedGenerationMethods',[])
            supported='generateContent' in methods
            print(json.dumps({'task':task,'model':model,'generateContent':supported,'ok':supported}))
            if not supported:return 1
        if args.text:
            criteria=GeminiIntentExtractorService(provider,IntentExtractorService()).extractCriteria(args.text)
            print(json.dumps(criteria.to_dict(),ensure_ascii=False,indent=2))
            if criteria.intentProvider!='gemini':return 1
        return 0
    except (AIUnavailable,DomainError) as exc: print(str(exc));return 1
    except (httpx.HTTPError,ValueError): print('Không kiểm tra được Gemini. Hãy kiểm tra kết nối/cấu hình.');return 1

if __name__=='__main__':raise SystemExit(main())

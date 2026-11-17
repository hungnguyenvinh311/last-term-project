import base64
import json
import httpx
import pytest
from Model.application.ai.GeminiClient import GeminiClient
from Model.application.ai.GeminiSpeechTranscriberService import GeminiSpeechTranscriberService
from Model.application.ai.GeminiIntentExtractorService import GeminiIntentExtractorService
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.errors import AIUnavailable,DomainError

def client(handler,config=None):
    settings=config if config is not None else {'APP_GEMINI_API_KEY':'test-gemini-secret'}
    return GeminiClient(lambda:dict(settings),lambda **kw:httpx.Client(transport=httpx.MockTransport(handler),**kw))

def result(answer,reason='STOP'):
    return httpx.Response(200,json={'candidates':[{'finishReason':reason,'content':{'parts':[{'text':json.dumps(answer,ensure_ascii=False)}]}}]})

def test_audio_is_inline_webm_and_transcript_is_structured():
    content=b'webm-fixture';seen=[]
    def handler(request):
        assert request.url.host=='generativelanguage.googleapis.com'
        assert request.url.path.endswith('/models/gemini-3.1-flash-lite:generateContent')
        assert 'key=' not in str(request.url) and request.headers['x-goog-api-key']=='test-gemini-secret'
        payload=json.loads(request.content);seen.append(payload)
        media=payload['contents'][0]['parts'][1]['inlineData']
        assert media['mimeType']=='audio/webm' and base64.b64decode(media['data'])==content
        assert payload['generationConfig']['responseMimeType']=='application/json'
        return result({'transcript':'điện thoại Samsung dưới 10 triệu'})
    assert GeminiSpeechTranscriberService(client(handler)).transcribe(content,'recording.webm')=='điện thoại Samsung dưới 10 triệu'
    assert len(seen)==1

def test_intent_schema_and_numeric_constraints():
    answer={'supported':True,'categoryID':1,'brand':'Samsung','maxPrice':10_000_000,
            'excludedTerms':['Xiaomi'],'specs':{'ram':{'value':8,'op':'min','unit':'gb'}}}
    def handler(request):
        payload=json.loads(request.content)
        assert 'supported' in payload['generationConfig']['responseJsonSchema']['properties']
        return result(answer)
    criteria=GeminiIntentExtractorService(client(handler),IntentExtractorService()).extractCriteria('điện thoại Samsung dưới 10 triệu RAM ít nhất 8GB không Xiaomi')
    assert criteria.categoryID==1 and criteria.brand=='Samsung' and criteria.maxPrice==10_000_000
    assert criteria.specs['ram']=={'value':8,'op':'min','unit':'gb'}
    assert criteria.excludedTerms==['xiaomi'] and criteria.intentProvider=='gemini' and criteria.intentWarning is None

@pytest.mark.parametrize('status,expected',[(400,'không chấp nhận'),(401,'API key'),(403,'API key'),(404,'model'),(429,'hạn mức'),(500,'đang lỗi')])
def test_errors_never_leak_provider_body_or_key(status,expected):
    provider=client(lambda request:httpx.Response(status,json={'error':{'message':'private test-gemini-secret'}}))
    with pytest.raises(AIUnavailable) as error:provider.generate('intent',[{'text':'test'}],'instruction',{})
    assert expected in str(error.value)
    assert 'test-gemini-secret' not in str(error.value) and 'private' not in str(error.value)

def test_missing_key_does_not_make_a_request_and_rules_fallback_is_visible(monkeypatch):
    monkeypatch.delenv('APP_GEMINI_API_KEY',raising=False);monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    def forbidden(request): raise AssertionError('No network with no key')
    provider=client(forbidden,{})
    with pytest.raises(AIUnavailable,match='APP_GEMINI_API_KEY'):GeminiSpeechTranscriberService(provider).transcribe(b'audio','test.webm')
    criteria=GeminiIntentExtractorService(provider,IntentExtractorService()).extractCriteria('điện thoại dưới 10 triệu')
    assert criteria.intentProvider=='rules' and 'dự phòng' in criteria.intentWarning
    assert criteria.categoryID==1 and criteria.maxPrice==10_000_000

@pytest.mark.parametrize('answer',[
    {'supported':True,'categoryID':99},
    {'supported':True,'minPrice':20_000_000,'maxPrice':10_000_000},
    {'supported':True,'specs':{'ram':{'value':8,'op':'min','unit':'mah'}}},
    {'supported':True,'sql':'untrusted instructions'},
])
def test_invalid_output_uses_validated_rules_without_exposing_input(answer):
    criteria=GeminiIntentExtractorService(client(lambda request:result(answer)),IntentExtractorService()).extractCriteria('điện thoại Samsung dưới 10 triệu')
    assert criteria.intentProvider=='rules' and criteria.maxPrice==10_000_000
    assert 'sai schema' in criteria.intentWarning and 'untrusted' not in criteria.intentWarning

def test_unsupported_query_is_not_silently_relaxed():
    service=GeminiIntentExtractorService(client(lambda request:result({'supported':False})),IntentExtractorService())
    with pytest.raises(DomainError):service.extractCriteria('máy giặt')

@pytest.mark.parametrize('answer,reason',[({'transcript':''},'STOP'),({'transcript':'unfinished'},'MAX_TOKENS'),({'unexpected':'answer'},'STOP')])
def test_silence_truncation_and_invalid_transcript_fail(answer,reason):
    service=GeminiSpeechTranscriberService(client(lambda request:result(answer,reason)))
    with pytest.raises(AIUnavailable):service.transcribe(b'audio','test.webm')

def test_replaced_key_and_model_are_read_each_request():
    config={'APP_GEMINI_API_KEY':'test-old','APP_GEMINI_TRANSCRIBE_MODEL':'gemini-3.1-flash-lite'};seen=[]
    def handler(request):
        seen.append((request.headers['x-goog-api-key'],request.url.path));return result({'transcript':'test'})
    service=GeminiSpeechTranscriberService(client(handler,config))
    service.transcribe(b'audio','test.webm');config['APP_GEMINI_API_KEY']='test-new';config['APP_GEMINI_TRANSCRIBE_MODEL']='gemini-2.5-flash-lite'
    service.transcribe(b'audio','test.webm')
    assert seen[0][0]=='test-old' and seen[1][0]=='test-new' and 'gemini-2.5-flash-lite' in seen[1][1]

def test_bad_model_and_audio_type_rejected_before_http():
    provider=client(lambda request:result({}),{'APP_GEMINI_API_KEY':'test','APP_GEMINI_TRANSCRIBE_MODEL':'../private?key=secret'})
    with pytest.raises(AIUnavailable,match='model'):GeminiSpeechTranscriberService(provider).transcribe(b'audio','test.webm')
    with pytest.raises(DomainError):GeminiSpeechTranscriberService(provider).transcribe(b'audio','test.exe')

def test_service_outage_short_circuit_expires_and_key_change_is_not_blocked(monkeypatch):
    import importlib
    module=importlib.import_module('Model.application.ai.GeminiClient')
    clock=[100.0];monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    config={'APP_GEMINI_API_KEY':'first'};calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(503,json={'error':{'message':'private'}})
    provider=client(handler,config)
    for _ in range(2):
        with pytest.raises(AIUnavailable):provider.generate('intent',[], '',{})
    assert len(calls)==1
    clock[0]+=31
    with pytest.raises(AIUnavailable):provider.generate('intent',[],'',{})
    assert len(calls)==2
    config['APP_GEMINI_API_KEY']='replacement'
    with pytest.raises(AIUnavailable):provider.generate('intent',[],'',{})
    assert len(calls)==3

from io import BytesIO
from PIL import Image
import httpx
import pytest
from Model.application.errors import AIUnavailable,DomainError
from Model.application.ai.SpeechTranscriberService import SpeechTranscriberService
from Model.application.integration.storage.LocalMediaStorage import LocalMediaStorage

def test_transcription_missing_key_and_provider_contract(monkeypatch):
    monkeypatch.delenv('APP_OPENAI_API_KEY',raising=False)
    service=SpeechTranscriberService(config_provider=lambda:{})
    with pytest.raises(AIUnavailable):service.transcribe(b'audio','test.webm')
    monkeypatch.setenv('APP_OPENAI_API_KEY','test-key-not-real')
    factory=httpx.Client
    def handler(request):
        assert request.url.path.endswith('/audio/transcriptions')
        content=request.read()
        assert b'name="language"' in content and b'\r\nvi\r\n' in content
        return httpx.Response(200,json={'text':'điện thoại Samsung'})
    monkeypatch.setattr(httpx,'Client',lambda **kw:factory(transport=httpx.MockTransport(handler)))
    assert service.transcribe(b'audio','test.webm')=='điện thoại Samsung'

@pytest.mark.parametrize('status,code,message',[(401,'expired_secret_key','hết hạn'),(429,'insufficient_quota','hạn mức'),(404,'model_not_found','quyền dùng model')])
def test_provider_errors_are_actionable_and_redacted(monkeypatch,status,code,message):
    factory=httpx.Client
    transport=httpx.MockTransport(lambda request:httpx.Response(status,json={'error':{'code':code,'message':'private provider details'}}))
    monkeypatch.setattr(httpx,'Client',lambda **kw:factory(transport=transport))
    service=SpeechTranscriberService(lambda:{'APP_OPENAI_API_KEY':'test-secret'})
    with pytest.raises(AIUnavailable) as error:service.transcribe(b'audio','test.webm')
    assert message in str(error.value)
    assert 'test-secret' not in str(error.value) and 'private provider details' not in str(error.value)

def test_transcription_reads_replaced_key_without_restart(monkeypatch):
    config={'APP_OPENAI_API_KEY':'test-old-key'};seen=[];factory=httpx.Client
    def handler(request):
        seen.append(request.headers['Authorization']);return httpx.Response(200,json={'text':'test transcript'})
    monkeypatch.setattr(httpx,'Client',lambda **kw:factory(transport=httpx.MockTransport(handler)))
    service=SpeechTranscriberService(lambda:dict(config))
    service.transcribe(b'audio','test.webm');config['APP_OPENAI_API_KEY']='test-new-key';service.transcribe(b'audio','test.webm')
    assert seen==['Bearer test-old-key','Bearer test-new-key']

def test_media_paths_and_upload_content(tmp_path):
    media=LocalMediaStorage(tmp_path)
    with pytest.raises(DomainError):media.validateImage(b'fake jpg')
    with pytest.raises(DomainError):media.resolveProductImage('../outside.jpg')
    content=BytesIO();Image.new('RGB',(100,100),'white').save(content,'PNG')
    reference=media.saveUpload(content.getvalue(),'image')
    assert media.read(reference)
    with pytest.raises(DomainError):media.read('../private.txt')

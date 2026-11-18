from pathlib import Path

import pytest

from Model.application.ai.FallbackSpeechTranscriberService import FallbackSpeechTranscriberService
from Model.application.ai.FasterWhisperTranscriberService import FasterWhisperTranscriberService
from Model.application.errors import AIUnavailable, DomainError


class Segment:
    def __init__(self, text):
        self.text = text


def test_faster_whisper_transcribes_vietnamese_and_removes_temporary_audio():
    observed = {}

    class Model:
        def transcribe(self, path, **options):
            observed['path'] = Path(path)
            observed['bytes'] = observed['path'].read_bytes()
            observed['options'] = options
            return iter([Segment('điện thoại Samsung'), Segment('màu xanh')]), object()

    service = FasterWhisperTranscriberService(
        model_factory=lambda *args, **kwargs: Model(),
        config_provider=lambda key: '.' if key == 'APP_FASTER_WHISPER_CACHE' else None,
        temporary_directory='.',
    )

    result = service.transcribe(b'fake audio bytes', 'voice.webm')

    assert result == 'điện thoại Samsung màu xanh'
    assert observed['bytes'] == b'fake audio bytes'
    assert observed['path'].suffix == '.webm'
    assert not observed['path'].exists()
    assert observed['options'] == {'language': 'vi', 'vad_filter': True}


def test_faster_whisper_rejects_unsupported_audio_type():
    service = FasterWhisperTranscriberService(model_factory=lambda *args, **kwargs: None)

    with pytest.raises(DomainError, match='Định dạng audio không hỗ trợ'):
        service.transcribe(b'fake audio bytes', 'voice.txt')


def test_fallback_uses_local_whisper_when_gemini_is_unavailable():
    class Gemini:
        def transcribe(self, content, filename):
            raise AIUnavailable('Gemini unavailable')

    class LocalWhisper:
        def transcribe(self, content, filename):
            return 'đồng hồ thông minh'

    result = FallbackSpeechTranscriberService(Gemini(), LocalWhisper()).transcribe(b'audio', 'voice.webm')

    assert result == 'đồng hồ thông minh'


def test_successful_gemini_transcription_does_not_run_fallback():
    class Gemini:
        def transcribe(self, content, filename):
            return 'tai nghe không dây'

    class LocalWhisper:
        def transcribe(self, content, filename):
            raise AssertionError('Fallback should not run after primary succeeds')

    result = FallbackSpeechTranscriberService(Gemini(), LocalWhisper()).transcribe(b'audio', 'voice.webm')

    assert result == 'tai nghe không dây'


def test_fallback_reports_when_both_transcribers_fail():
    class Unavailable:
        def __init__(self, message):
            self.message = message

        def transcribe(self, content, filename):
            raise AIUnavailable(self.message)

    with pytest.raises(AIUnavailable, match='Gemini unavailable') as error:
        FallbackSpeechTranscriberService(
            Unavailable('Gemini unavailable'), Unavailable('local model unavailable')
        ).transcribe(b'audio', 'voice.webm')
    assert 'local model unavailable' in str(error.value)

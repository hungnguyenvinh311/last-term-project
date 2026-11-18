import os
import tempfile
from pathlib import Path
from threading import Lock

from Model.application.config.settings import ROOT
from Model.application.errors import AIUnavailable, DomainError


class FasterWhisperTranscriberService:
    """Local Vietnamese speech-to-text adapter; model loading is deferred until first use."""

    def __init__(self, model_factory=None, config_provider=None, temporary_directory=None):
        self.model_factory = model_factory
        self.config_provider = config_provider or os.getenv
        self.temporary_directory = temporary_directory
        self._model = None
        self._load_lock = Lock()

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            try:
                factory = self.model_factory
                if factory is None:
                    from faster_whisper import WhisperModel
                    factory = WhisperModel
                model_size = self.config_provider('APP_FASTER_WHISPER_MODEL') or 'small'
                device = self.config_provider('APP_FASTER_WHISPER_DEVICE') or 'cpu'
                compute_type = self.config_provider('APP_FASTER_WHISPER_COMPUTE_TYPE') or 'int8'
                cache_dir = Path(self.config_provider('APP_FASTER_WHISPER_CACHE') or
                                 (ROOT / 'data' / 'model_cache' / 'faster-whisper'))
                cache_dir.mkdir(parents=True, exist_ok=True)
                self._model = factory(model_size, device=device, compute_type=compute_type,
                                      download_root=str(cache_dir))
            except Exception as exc:
                raise AIUnavailable(
                    'Không thể khởi tạo faster-whisper. Hãy cài requirements-ai.txt và kiểm tra model/cache.'
                ) from exc
        return self._model

    def transcribe(self, content, filename):
        if not content or len(content) > 20 * 1024 * 1024:
            raise DomainError('Audio phải có dung lượng từ 1 byte đến 20 MB')
        suffix = Path(filename or '').suffix.lower()
        if suffix not in {'.webm', '.wav', '.mp3', '.mp4', '.m4a', '.ogg', '.flac'}:
            raise DomainError('Định dạng audio không hỗ trợ')

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False,
                                             dir=self.temporary_directory) as audio_file:
                audio_file.write(content)
                temporary_path = audio_file.name
            segments, _ = self._get_model().transcribe(temporary_path, language='vi', vad_filter=True)
            text = ' '.join(segment.text.strip() for segment in segments).strip()
            if not text:
                raise AIUnavailable('Whisper không nhận dạng được lời nói; hãy ghi âm lại hoặc nhập văn bản.')
            return text
        except (DomainError, AIUnavailable):
            raise
        except Exception as exc:
            raise AIUnavailable('Phiên âm bằng faster-whisper thất bại; hãy kiểm tra định dạng audio và model.') from exc
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)

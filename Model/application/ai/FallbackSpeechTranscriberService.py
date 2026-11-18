from Model.application.errors import AIUnavailable, DomainError


class FallbackSpeechTranscriberService:
    """Try the configured remote transcriber first, then a local backup."""

    def __init__(self, primary, fallback):
        self.primary, self.fallback = primary, fallback

    def transcribe(self, content, filename):
        try:
            return self.primary.transcribe(content, filename)
        except DomainError:
            raise
        except AIUnavailable as primary_error:
            try:
                return self.fallback.transcribe(content, filename)
            except DomainError:
                raise
            except AIUnavailable as fallback_error:
                raise AIUnavailable(
                    f'Phiên âm qua dịch vụ chính thất bại ({primary_error}); '
                    f'faster-whisper dự phòng cũng thất bại ({fallback_error}).'
                ) from None

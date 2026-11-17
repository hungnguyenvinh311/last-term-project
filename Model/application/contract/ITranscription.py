from typing import Protocol

class ITranscription(Protocol):
    def transcribe(self, content: bytes, filename: str) -> str: ...

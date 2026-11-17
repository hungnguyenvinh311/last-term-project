from dataclasses import dataclass
from .SearchQuery import SearchQuery

@dataclass
class VoiceQuery(SearchQuery):
    transcribedText: str = ""
    audioReference: str | None = None

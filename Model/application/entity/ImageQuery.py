from dataclasses import dataclass
from .SearchQuery import SearchQuery

@dataclass
class ImageQuery(SearchQuery):
    imageReference: str = ""
    selectedRegion: list[float] | None = None

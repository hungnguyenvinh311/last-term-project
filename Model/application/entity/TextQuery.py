from dataclasses import dataclass
from .SearchQuery import SearchQuery

@dataclass
class TextQuery(SearchQuery):
    queryText: str = ""

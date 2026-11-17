from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class SearchResult:
    queryID: int
    articleID: int
    rank: int
    score: float

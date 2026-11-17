from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class SearchQuery:
    queryID: int
    queryType: str
    searchCriteria: dict
    customerID: int | None = None
    createdAt: datetime | None = None

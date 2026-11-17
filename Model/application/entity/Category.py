from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Category:
    categoryID: int
    groupName: str
    subCategory: str
    specificationSchema: dict | None = None

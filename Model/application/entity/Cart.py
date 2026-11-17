from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Cart:
    cartID: int
    customerID: int
    createdAt: datetime | None = None
    updatedAt: datetime | None = None

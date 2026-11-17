from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class OrderItem:
    orderItemID: int
    orderID: int
    articleID: int
    quantity: int
    unitPrice: Decimal
    productNameSnapshot: str
    specificationSnapshot: dict | None = None
    warrantySnapshot: str | None = None

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Payment:
    paymentID: int
    orderID: int
    paymentMethod: str
    amount: Decimal
    status: str
    currency: str = 'VND'
    transactionCode: str | None = None
    paidAt: datetime | None = None

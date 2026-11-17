from dataclasses import dataclass
from decimal import Decimal
@dataclass
class PaymentOutcome:
    orderID: int
    amount: Decimal
    status: str
    transactionCode: str

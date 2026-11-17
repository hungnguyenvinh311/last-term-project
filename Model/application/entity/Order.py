from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Order:
    orderID: int
    customerID: int
    status: str
    totalAmount: Decimal
    paymentMethod: str
    shippingAddress: str
    recipientPhone: str
    currency: str = 'VND'
    itemSubTotal: Decimal = Decimal('0')
    discountAmount: Decimal = Decimal('0')
    shippingFee: Decimal = Decimal('0')
    createdAt: datetime | None = None
    holdExpireAt: datetime | None = None
    version: int = 1

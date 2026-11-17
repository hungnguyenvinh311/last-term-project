from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Shipment:
    shippingID: int
    orderID: int
    trackingNumber: str
    carrier: str
    status: str
    estimatedDeliveryDate: datetime | None = None
    deliveredAt: datetime | None = None

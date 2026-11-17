from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, date

@dataclass
class Customer:
    customerID: int
    fullName: str
    email: str
    phoneNumber: str | None = None
    shippingAddress: str | None = None
    dateOfBirth: date | None = None

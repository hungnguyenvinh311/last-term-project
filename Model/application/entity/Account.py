from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Account:
    accountID: int
    customerID: int
    email: str
    role: str
    isActive: bool

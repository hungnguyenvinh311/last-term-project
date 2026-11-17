from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class AuthSession:
    tokenHash: str
    accountID: int
    expiresAt: datetime
    createdAt: datetime | None = None

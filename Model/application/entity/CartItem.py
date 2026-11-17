from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class CartItem:
    cartItemID: int
    cartID: int
    articleID: int
    quantity: int

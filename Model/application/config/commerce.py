"""Demo pricing policy; no inventory or voucher storage is implied."""
import os
from decimal import Decimal


def shipping_fee():
    fee = Decimal(os.getenv('APP_DEMO_SHIPPING_FEE','0'))
    if not fee.is_finite() or fee<0 or fee>10000000 or fee.as_tuple().exponent < -2:
        raise ValueError('APP_DEMO_SHIPPING_FEE must be a nonnegative amount with at most two decimal places')
    return fee

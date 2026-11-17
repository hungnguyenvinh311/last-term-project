from decimal import Decimal
from Model.application.config.commerce import shipping_fee


class CheckoutPricingService:
    def calculate(self, items):
        subtotal=sum((Decimal(str(p['price'] or 0))*p['quantity'] for p in items),Decimal(0))
        fee=shipping_fee() if items else Decimal(0)
        return dict(itemSubTotal=subtotal,discountAmount=Decimal(0),shippingFee=fee,totalAmount=subtotal+fee,currency='VND')

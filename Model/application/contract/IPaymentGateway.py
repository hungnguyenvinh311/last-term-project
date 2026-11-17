from typing import Protocol

class IPaymentGateway(Protocol):
    def processPayment(self, orderId: int, amount, scenario: str): ...

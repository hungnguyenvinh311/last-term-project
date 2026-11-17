from typing import Protocol


class ICheckoutPricing(Protocol):
    def calculate(self, items:list): ...

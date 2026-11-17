from typing import Protocol

class IRecommendation(Protocol):
    def recommendForProduct(self, articleID: int, limit=8): ...

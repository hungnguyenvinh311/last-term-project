from .ProductCandidate import ProductCandidate
class RankedProduct(ProductCandidate, total=False):
    rank: int
    score: float
    fallback: bool

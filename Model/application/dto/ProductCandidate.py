from typing import TypedDict
class ProductCandidate(TypedDict, total=False):
    articleID: int
    similarity: float | None
    lexical: float

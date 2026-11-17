from typing import TypedDict
class RecommendationResponse(TypedDict):
    sourceArticleID: int
    products: list[dict]
    fallback: bool
    message: str

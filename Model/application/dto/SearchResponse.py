from typing import TypedDict,NotRequired
class SearchResponse(TypedDict):
    queryID: int
    queryType: str
    criteria: dict
    products: list[dict]
    fallback: bool
    message: str
    imageSelection: NotRequired[dict]

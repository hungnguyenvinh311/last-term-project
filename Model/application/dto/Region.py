from typing import TypedDict
class Region(TypedDict):
    label: str
    score: float
    region: list[float]

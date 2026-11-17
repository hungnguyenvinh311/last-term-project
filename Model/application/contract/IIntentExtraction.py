from typing import Protocol

class IIntentExtraction(Protocol):
    def extractCriteria(self, text: str): ...

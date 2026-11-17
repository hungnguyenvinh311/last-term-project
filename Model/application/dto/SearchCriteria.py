from dataclasses import dataclass, field, asdict

@dataclass
class SearchCriteria:
    text: str = ''
    categoryID: int | None = None
    brand: str | None = None
    minPrice: float | None = None
    maxPrice: float | None = None
    requiredTerms: list[str] = field(default_factory=list)
    excludedTerms: list[str] = field(default_factory=list)
    preferredTerms: list[str] = field(default_factory=list)
    specs: dict = field(default_factory=dict)
    intentProvider: str = 'rules'
    intentWarning: str | None = None
    def to_dict(self): return asdict(self)

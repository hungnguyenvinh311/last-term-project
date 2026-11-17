from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from collections.abc import Mapping

@dataclass
class Product(Mapping):
    articleID: int
    categoryID: int
    productName: str
    price: Decimal
    currency: str
    brand: str | None = None
    technicalSpecs: dict | None = None
    imagePath: str | None = None
    imageEmbedding: list[float] | None = None
    textEmbedding: list[float] | None = None
    description: str | None = None
    warrantyTerms: str | None = None
    isActive: bool = True
    representationUpdateAt: datetime | None = None
    subCategory: str | None = None
    onHandQuantity: int = 0
    availableQuantity: int = 0

    def __getitem__(self,key): return self.__dict__[key]
    def __iter__(self): return iter(self.__dict__)
    def __len__(self): return len(self.__dict__)

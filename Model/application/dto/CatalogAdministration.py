from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    categoryID: int = Field(ge=1, le=10000)
    productName: str = Field(min_length=1, max_length=255)
    brand: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=20000)
    technicalSpecs: dict = Field(default_factory=dict)
    warrantyTerms: str = Field(default='Bảo hành 12 tháng', min_length=1, max_length=10000)
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: Literal['VND'] = 'VND'
    isActive: bool = True

    @field_validator('technicalSpecs')
    @classmethod
    def specs(cls, value):
        if len(value) > 100 or any(len(k) > 100 or not isinstance(v, (str,int,float,bool,type(None)))
                                   or len(str(v)) > 2000 for k,v in value.items()):
            raise ValueError('Technical specifications must be simple name/value pairs')
        return value


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    groupName: str = Field(min_length=1, max_length=100)
    subCategory: str = Field(min_length=1, max_length=100)

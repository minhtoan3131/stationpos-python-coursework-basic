from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductListDTO:
    id: int
    sku: str
    name: str
    category_name: str
    unit_name: str
    retail_price: float
    wholesale_price: Optional[float]
    barcode: Optional[str]
    supplier_name: Optional[str]
    conversion_unit_name: Optional[str] = None
    conversion_ratio: Optional[float] = None
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductCreateDTO:
    sku: str

    name: str

    barcode: Optional[str]

    category_id: int
    supplier_id: int

    base_unit_id: int

    retail_price: float
    wholesale_price: float
    cost_price: float

    min_stock: int

    description: Optional[str]

    conversion_unit_id: Optional[int]
    conversion_ratio: Optional[float]
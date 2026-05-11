from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductDetailDTO:
    id: int

    sku: str
    barcode: Optional[str]

    name: str
    description: Optional[str]

    category_id: int
    category_name: str

    supplier_id: int
    supplier_name: str

    base_unit_id: int
    base_unit_name: str

    retail_price: float
    wholesale_price: float

    conversion_unit_id: Optional[int]
    conversion_unit_name: Optional[str]

    conversion_ratio: Optional[float]

    min_stock: int

    is_active: bool

    cost_price: float
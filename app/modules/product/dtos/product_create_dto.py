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

    min_stock: int

    description: Optional[str]

    conversion_unit_id: Optional[int]
    conversion_ratio: Optional[float]

    # GIÁ TRỊ MẶC ĐỊNH
    cost_price: float = 0.0
    retail_price: float = 0.0
    wholesale_price: float = 0.0
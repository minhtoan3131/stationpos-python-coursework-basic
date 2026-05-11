from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass
class ProductImportDTO:
    id: int
    sku: str
    name: str
    base_unit_id: int
    base_unit_name: str
    cost_price: Decimal
    # Thông tin quy đổi (có thể Null)
    conversion_unit_id: Optional[int] = None
    conversion_unit_name: Optional[str] = None
    conversion_ratio: Optional[Decimal] = None
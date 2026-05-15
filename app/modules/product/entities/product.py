from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import datetime


@dataclass
class Product:
    id: Optional[int]

    sku: str
    name: str

    barcode: Optional[str]

    category_id: int
    supplier_id: int

    base_unit_id: int

    cost_price: Decimal
    retail_price: Decimal
    wholesale_price: Decimal

    min_stock: int

    description: Optional[str]

    is_active: bool

    created_at: Optional[datetime]
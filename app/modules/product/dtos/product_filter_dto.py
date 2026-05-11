from dataclasses import dataclass
from typing import Optional

@dataclass
class ProductFilterDTO:
    keyword: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    is_active: Optional[bool] = True
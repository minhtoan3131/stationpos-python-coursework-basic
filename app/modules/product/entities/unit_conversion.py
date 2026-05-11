from dataclasses import dataclass
from typing import Optional


@dataclass
class UnitConversion:
    id: Optional[int]

    product_id: int

    from_unit_id: int
    to_unit_id: int

    ratio: float
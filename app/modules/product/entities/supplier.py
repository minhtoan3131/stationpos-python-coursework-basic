from dataclasses import dataclass
from typing import Optional


@dataclass
class Supplier:
    id: Optional[int]

    name: str
    phone: Optional[str]
    address: Optional[str]
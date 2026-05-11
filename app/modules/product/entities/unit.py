from dataclasses import dataclass
from typing import Optional

@dataclass
class Unit:
    id: Optional[int]
    name: str
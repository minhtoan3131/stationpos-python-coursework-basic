from abc import ABC, abstractmethod
from typing import List, Dict, Any

class UnitService(ABC):
    @abstractmethod
    def get_all_units(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_unit(self, name: str) -> int:
        pass
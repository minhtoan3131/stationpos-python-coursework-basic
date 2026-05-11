from abc import ABC, abstractmethod
from typing import List, Dict, Any

class UnitRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def exists_by_name(self, name: str) -> bool:
        pass

    @abstractmethod
    def exists_by_id(self, unit_id: int) -> bool:
        pass

    @abstractmethod
    def create(self, name: str) -> int:
        pass
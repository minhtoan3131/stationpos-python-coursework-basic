from abc import ABC, abstractmethod
from typing import List, Dict, Any

class CategoryService(ABC):
    @abstractmethod
    def get_all_categories(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_category(self, name: str) -> int:
        pass
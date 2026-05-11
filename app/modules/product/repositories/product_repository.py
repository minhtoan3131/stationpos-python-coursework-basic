# app/modules/product/repositories/product_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.modules.product.entities.product import Product

class ProductRepository(ABC):
    # =========================
    # PRODUCT LIST & SEARCH
    # =========================
    @abstractmethod
    def get_product_list(self) -> List[dict]: pass

    @abstractmethod
    def search_products(self, keyword: Optional[str], category_id: Optional[int], supplier_id: Optional[int],
                        is_active: Optional[bool]) -> List[dict]: pass

    # =========================
    # CRUD
    # =========================
    @abstractmethod
    def get_product_by_id(self, product_id: int) -> Optional[Product]: pass

    @abstractmethod
    def create_product(self, product: Product) -> int: pass

    @abstractmethod
    def update_product(self, product: Product) -> bool: pass

    @abstractmethod
    def soft_delete_product(self, product_id: int) -> bool: pass

    # =========================
    # VALIDATION (SKU & BARCODE)
    # =========================
    @abstractmethod
    def exists_by_sku(self, sku: str) -> bool: pass

    @abstractmethod
    def exists_by_sku_excluding_id(self, sku: str, product_id: int) -> bool: pass

    @abstractmethod
    def get_by_barcode(self, barcode: str) -> Optional[Product]: pass

    @abstractmethod
    def exists_by_barcode(self, barcode: str) -> bool: pass

    @abstractmethod
    def exists_by_barcode_excluding_id(self, barcode: str, product_id: int) -> bool: pass
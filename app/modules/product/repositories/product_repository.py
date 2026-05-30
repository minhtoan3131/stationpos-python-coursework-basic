# app/modules/product/repositories/product_repository.py
from abc import ABC, abstractmethod
from decimal import Decimal
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

    @abstractmethod
    def get_product_import_detail(self, product_id: int) -> Optional[dict]: pass

    @abstractmethod
    def get_product_detail_for_import(self, product_id: int) -> Optional[dict]:
        """Lấy thông tin chi tiết sản phẩm kèm theo ĐVT và quy đổi cho nghiệp vụ nhập hàng"""
        pass

    @abstractmethod
    def update_cost_price(self, product_id: int, new_cost_price: Decimal) -> None:
        """Cập nhật lại Giá vốn bình quân (MAC) bằng kiểu Decimal"""
        pass

    @abstractmethod
    def get_product_sale_list(self, keyword: str = None) -> List[dict]: pass

    @abstractmethod
    def update_selling_prices(self, product_id: int, retail_price: float, wholesale_price: float) -> bool:
        """Cập nhật giá bán lẻ và giá sỉ của sản phẩm dưới database."""
        pass

    @abstractmethod
    def has_historical_transactions(self, product_id: int) -> bool:
        """Kiểm tra xem sản phẩm đã phát sinh bất kỳ lịch sử mua hoặc bán nào chưa"""
        pass
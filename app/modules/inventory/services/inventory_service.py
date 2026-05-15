from abc import ABC, abstractmethod
from typing import List
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, InventoryListDTO
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO


class InventoryService(ABC):

    @abstractmethod
    def get_inventory_list(self, search_keyword: str = None) -> List[InventoryListDTO]:
        """
        Lấy danh sách tồn kho để hiển thị lên bảng.
        - search_keyword: Dùng để lọc theo SKU hoặc Tên sản phẩm.
        - Trả về: Danh sách các InventoryListDTO đã được tính toán quy đổi Sỉ/Lẻ.
        """
        pass

    @abstractmethod
    def create_purchase_order(self, dto: PurchaseOrderCreateDTO) -> int:
        """
        Xử lý lưu phiếu nhập hàng và cộng dồn tồn kho.
        - Hàm này phải đảm bảo tính Transaction (Lưu phiếu -> Lưu chi tiết -> Ghi log -> Cộng kho).
        - Hàm này thực hiện quy đổi Số lượng Hộp -> Số lượng Cây trước khi cộng kho.
        - Trả về: ID của Phiếu nhập vừa tạo.
        """
        pass

    @abstractmethod
    def search_products_for_import(self, keyword: str) -> List[ProductDetailDTO]:
        """Tìm sản phẩm nhanh để đưa vào phiếu nhập (lấy cả thông tin quy đổi)"""
        pass

    @abstractmethod
    def export_inventory_to_excel(self, file_path: str) -> bool:
        """
        Xuất dữ liệu tồn kho hiện tại ra file Excel theo đường dẫn chỉ định.
        Trả về True nếu lưu thành công, ném ra Exception nếu có lỗi.
        """
        pass
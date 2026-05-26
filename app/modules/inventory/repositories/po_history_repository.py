from abc import ABC, abstractmethod


class PurchaseOrderHistoryRepository(ABC):

    @abstractmethod
    def search_purchase_orders(self, from_date: str, to_date: str, keyword: str = None, status: str = 'ALL') -> list:
        """Truy vấn danh sách phiếu nhập dựa trên bộ lọc"""
        pass

    @abstractmethod
    def get_purchase_order_by_id(self, po_id: int) -> dict:
        """Lấy thông tin Header (Master) của 1 phiếu nhập cụ thể"""
        pass

    @abstractmethod
    def get_purchase_order_items(self, po_id: int) -> list:
        """Lấy danh sách các mặt hàng chi tiết thuộc phiếu nhập đó"""
        pass

    @abstractmethod
    def update_purchase_order_status(self, po_id: int, new_status: str, cancel_reason: str = None) -> None:
        """Cập nhật trạng thái phiếu và lưu lý do hủy"""
        pass

    @abstractmethod
    def has_subsequent_delivery_transactions(self, product_id: int, po_created_at) -> bool:
        """Kiểm tra xem có bất kỳ giao dịch XUẤT KHO nào phát sinh SAU thời điểm (timestamp) của phiếu nhập này không."""
        pass
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ReportRepository(ABC):
    @abstractmethod
    def get_kpi_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Lấy tổng doanh thu, lợi nhuận, số hóa đơn trong khoảng thời gian và tổng giá trị tồn kho hiện tại."""
        pass

    @abstractmethod
    def get_revenue_trend(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Lấy doanh thu theo từng ngày để vẽ biểu đồ xu hướng."""
        pass

    @abstractmethod
    def get_top_products(self, start_date: str, end_date: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Lấy top các sản phẩm bán chạy nhất theo số lượng."""
        pass

    @abstractmethod
    def get_transaction_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Lấy lịch sử giao dịch hóa đơn."""
        pass

    @abstractmethod
    def get_inventory_valuation(self) -> List[Dict[str, Any]]:
        """Lấy báo cáo giá trị tồn kho hiện tại (không phụ thuộc ngày lọc)."""
        pass
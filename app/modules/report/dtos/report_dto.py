from dataclasses import dataclass
from decimal import Decimal
from typing import List

@dataclass
class KPIDTO:
    """DTO chứa trọn vẹn bộ chỉ số kiểm toán hiển thị trên 8 thẻ KPI mới."""
    total_orders_created: int       # Tổng đơn phát sinh
    total_orders_completed: int     # Đơn thành công
    total_orders_cancelled: int     # Đơn đã hủy
    gross_revenue: Decimal          # Doanh thu thô phát sinh
    cancelled_value: Decimal        # Giá trị hóa đơn hủy hoàn
    net_revenue: Decimal            # Doanh thu thuần thực thu
    total_cogs: Decimal             # Tổng giá vốn hàng bán
    gross_profit: Decimal           # Lợi nhuận gộp bán hàng
    variance_garbage: Decimal       # Điều chỉnh chênh lệch kế toán rác
    net_profit: Decimal             # Lợi nhuận thuần thực tế thực nhận

@dataclass
class RevenueTrendItemDTO:
    """DTO cho từng điểm dữ liệu trên biểu đồ xu hướng doanh thu."""
    date: str                  # Ngày định dạng dạng chuỗi (VD: "27/10")
    revenue: Decimal           # Doanh thu của ngày đó

@dataclass
class TopProductDTO:
    """DTO cho từng sản phẩm nằm trong danh sách bán chạy."""
    product_name: str          # Tên sản phẩm
    quantity: int              # Tổng số lượng đã bán lẻ/sỉ (quy đổi về đơn vị cơ bản)

@dataclass
class TransactionHistoryDTO:
    """DTO cho mỗi dòng hiển thị trong bảng Lịch sử giao dịch hóa đơn."""
    invoice_code: str          # Mã hóa đơn
    created_at: str            # Thời gian lập hóa đơn (VD: "2023-10-27 08:30:00")
    total_amount: Decimal      # Tổng tiền hóa đơn (sau chiết khấu)
    payment_method: str        # Hình thức thanh toán đã chuyển đổi ngôn ngữ ("Tiền mặt", "Chuyển khoản")

@dataclass
class InventoryReportDTO:
    """DTO cho mỗi dòng hiển thị trong bảng Báo cáo giá trị tồn kho hiện tại."""
    product_name: str          # Tên sản phẩm
    unit_name: str             # Tên đơn vị tính lẻ cơ bản
    stock_quantity: int        # Số lượng tồn kho hiện tại
    mac_price: Decimal         # Giá vốn tính theo phương pháp MAC hiện tại
    total_inventory_value: Decimal # Tổng giá trị tồn kho của mặt hàng này (SL x Giá vốn)

@dataclass
class DashboardReportDTO:
    """DTO tổng hợp toàn bộ dữ liệu cần thiết cho màn hình báo cáo."""
    kpis: KPIDTO
    revenue_trend: List[RevenueTrendItemDTO]
    top_products: List[TopProductDTO]
    transactions: List[TransactionHistoryDTO]
    inventory_valuation: List[InventoryReportDTO]
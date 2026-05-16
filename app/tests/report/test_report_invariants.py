import pytest
import copy
from decimal import Decimal
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl


# ==========================================
# SETUP FAKE DATABASE & REPOSITORY
# ==========================================
class FakeReportRepository:
    def __init__(self):
        # Dữ liệu gốc dùng làm mồi để kiểm chứng tính nhất quán
        self.raw_kpis = {
            "total_orders": 2,
            "total_revenue": Decimal("300000"),
            "total_profit": Decimal("120000"),
            "total_stock_value": Decimal("500000")
        }
        self.raw_trend = [
            {"date": "15/05", "revenue": Decimal("100000")},
            {"date": "16/05", "revenue": Decimal("200000")}
        ]
        self.raw_top_products = [
            {"product_name": "Bút bi Thiên Long", "quantity": 50}
        ]
        self.raw_transactions = [
            {"invoice_code": "HD01", "created_at": "2026-05-15 10:00", "final_amount": Decimal("100000"),
             "payment_method": "Tiền mặt"}
        ]
        self.raw_inventory = [
            {"product_name": "Bút bi Thiên Long", "unit_name": "Cây", "stock_quantity": 50,
             "mac_price": Decimal("4000"), "total_inventory_value": Decimal("200000")},
            {"product_name": "Vở kẻ ngang", "unit_name": "Cuốn", "stock_quantity": 30, "mac_price": Decimal("10000"),
             "total_inventory_value": Decimal("300000")}
        ]

    def get_kpi_metrics(self, start_date: str, end_date: str): return self.raw_kpis

    def get_revenue_trend(self, start_date: str, end_date: str): return self.raw_trend

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5): return self.raw_top_products

    def get_transaction_history(self, start_date: str, end_date: str): return self.raw_transactions

    def get_inventory_valuation(self): return self.raw_inventory


class FakeUnitOfWork:
    def __init__(self, repo):
        self.report_repo = repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES THIẾT LẬP
# ==========================================
@pytest.fixture
def fake_repo():
    return FakeReportRepository()


@pytest.fixture
def report_service(fake_repo):
    uow_factory = lambda: FakeUnitOfWork(fake_repo)
    return ReportServiceImpl(uow_factory)


# ==========================================
# TRIỂN KHAI CÁC BÀI TEST BẤT BIẾN (INVARIANTS)
# ==========================================

def test_report_invariant_internal_consistency(report_service):
    """
    TC_Inv_01: Kiểm chứng tính nhất quán dữ liệu nội bộ tài chính.
    Các con số tổng hợp trên thẻ KPI bắt buộc phải khớp 100% với dữ liệu chi tiết ở các bảng biểu.
    """
    # ACT: Lấy dữ liệu DTO tổng hợp từ cửa ngõ Service
    report_data = report_service.get_dashboard_report("2026-05-15", "2026-05-16")

    # THEN: Xác thực tính nhất quán toán học
    # 1. Tổng doanh thu hiển thị trên thẻ KPI bắt buộc phải bằng tổng doanh thu biểu đồ xu hướng cộng lại
    sum_trend_revenue = sum(item.revenue for item in report_data.revenue_trend)
    assert report_data.kpis.total_revenue == sum_trend_revenue

    # 2. Tổng giá trị kho hiển thị trên thẻ KPI bắt buộc phải bằng tổng giá trị tồn của từng mặt hàng cộng lại
    sum_inventory_value = sum(item.total_inventory_value for item in report_data.inventory_valuation)
    assert report_data.kpis.total_stock_value == sum_inventory_value

    # 3. Luật kinh doanh sống còn: Lợi nhuận gộp không bao giờ được phép vượt quá tổng doanh thu
    assert report_data.kpis.total_profit <= report_data.kpis.total_revenue


def test_report_invariant_read_only_safety(report_service, fake_repo):
    """
    TC_Inv_02: Kiểm chứng ràng buộc an toàn Idempotent (Read-Only).
    Thao tác xem báo cáo tuyệt đối không được để lại bất kỳ side-effect thay đổi dữ liệu nào trong DB.
    """
    # GIVEN: Chụp ảnh Snapshot trạng thái toàn bộ "Database RAM" của Repo trước khi thực thi
    repo_snapshot = copy.deepcopy(fake_repo.__dict__)

    # ACT: Gọi hàm xem báo cáo liên tục
    report_service.get_dashboard_report("2026-05-15", "2026-05-16")

    # THEN: Đối chiếu dữ liệu của Repo sau khi chạy. Bắt buộc phải nguyên vẹn, trùng khớp 100% với ảnh chụp ban đầu.
    assert fake_repo.__dict__ == repo_snapshot


def test_report_invariant_atomic_failure_on_crash(fake_repo):
    """
    TC_Inv_03: Kiểm chứng tính toàn vẹn khi xảy ra sự cố (Atomic Failure).
    Nếu bất kỳ truy vấn con nào bị lỗi, hệ thống phải sập tập trung, cấm trả về một DTO lỗi một nửa.
    """

    # GIVEN: Tạo ra một Repo đột biến giả lập tình huống phân hệ Xu hướng doanh thu bị sập / timeout kĩ thuật
    def buggy_get_revenue_trend(start_date, end_date):
        raise RuntimeError("Database Connection Timeout! Phân hệ Xu hướng doanh thu bị sập.")

    fake_repo.get_revenue_trend = buggy_get_revenue_trend

    # Khởi tạo service bọc quanh repo lỗi
    service = ReportServiceImpl(lambda: FakeUnitOfWork(fake_repo))

    # WHEN & THEN: Gọi service và đảm bảo lỗi kỹ thuật được đẩy thẳng lên trên an toàn để kích hoạt hệ thống rollback/log lỗi
    with pytest.raises(RuntimeError) as exc_info:
        service.get_dashboard_report("2026-05-15", "2026-05-16")

    # Đảm bảo thông báo lỗi gốc không bị nuốt chửng hay che giấu, phục vụ việc khoanh vùng vết lỗi (Stack trace)
    assert "Database Connection Timeout!" in str(exc_info.value)
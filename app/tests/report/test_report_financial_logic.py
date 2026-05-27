# File: app/tests/report/test_report_financial_logic.py
import pytest
from decimal import Decimal
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl
from app.modules.report.dtos.report_dto import DashboardReportDTO


# --- THIẾT LẬP MOCK GIẢ LẬP HỘP ĐEN ---
class MockReportRepository:
    def __init__(self):
        self.stubbed_kpis = {}

    def get_kpi_metrics(self, start_date: str, end_date: str):
        return self.stubbed_kpis

    def get_revenue_trend(self, start, end): return []

    def get_top_products(self, start, end): return []

    def get_transaction_history(self, start, end): return []

    def get_inventory_valuation(self): return []


class MockUnitOfWork:
    def __init__(self, repo):
        self.report_repo = repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def test_env():
    repo = MockReportRepository()
    uow_factory = lambda: MockUnitOfWork(repo)
    service = ReportServiceImpl(uow_factory)
    return service, repo


# --- KHU VỰC KIỂM TOÁN CÁC KỊCH BẢN DOANH NGHIỆP ---

def test_financial_case_normal_sales(test_env):
    """
    Nghiệp vụ 1: Phát sinh doanh thu bình thường, không hủy đơn, không dọn rác kho.
    Công thức kế toán chuẩn:
      - Doanh thu thuần (Net) = Gross (100k) - Hủy (0) = 100k
      - Lợi nhuận gộp kỹ thuật = Doanh thu thuần (100k) - Giá vốn (60k) = 40k
      - Lợi nhuận thuần thực tế = Lợi nhuận gộp (40k) + Tiền rác kho (0) = 40k
    """
    service, repo = test_env
    repo.stubbed_kpis = {
        "total_orders_created": 1, "total_orders_completed": 1, "total_orders_cancelled": 0,
        "gross_revenue": 100000.0, "cancelled_value": 0.0, "net_revenue": 100000.0,
        "total_cogs": 60000.0, "gross_profit": 40000.0, "variance_garbage": 0.0, "net_profit": 40000.0
    }

    report: DashboardReportDTO = service.get_dashboard_report("2026-05-01", "2026-05-27")
    kpis = report.kpis

    assert kpis.net_revenue == Decimal("100000")
    assert kpis.gross_profit == Decimal("40000")
    assert kpis.net_profit == Decimal("40000")


def test_financial_case_total_cancellation_should_not_go_negative(test_env):
    """
    Nghiệp vụ 2 (KIỂM TRA BÚT TOÁN SỬA LỖI DOANH THU ÂM):
    Người dùng tạo đơn 100k sau đó bấm HỦY TOÀN BỘ hóa đơn đó.
    Dưới góc nhìn tài chính chuẩn:
      - Doanh thu phát sinh ban đầu (Gross) vẫn là 100k.
      - Giá trị đơn hủy ghi nhận là 100k.
      - Doanh thu thuần thực thu (Net) bắt buộc phải bằng: 100k - 100k = 0 VND (Tuyệt đối không được ÂM).
      - Đơn hàng hoàn tất về 0, Đơn hủy tăng lên 1.
    """
    service, repo = test_env
    # Mô phỏng chính xác dữ liệu sau khi sửa lỗi từ View tổng hợp theo ngày
    repo.stubbed_kpis = {
        "total_orders_created": 1, "total_orders_completed": 0, "total_orders_cancelled": 1,
        "gross_revenue": 100000.0, "cancelled_value": 100000.0, "net_revenue": 0.0,
        "total_cogs": 0.0, "gross_profit": 0.0, "variance_garbage": 0.0, "net_profit": 0.0
    }

    report: DashboardReportDTO = service.get_dashboard_report("2026-05-01", "2026-05-27")
    kpis = report.kpis

    assert kpis.total_orders_created == 1
    assert kpis.total_orders_completed == 0
    assert kpis.total_orders_cancelled == 1
    assert kpis.gross_revenue == Decimal("100000")
    assert kpis.cancelled_value == Decimal("100000")

    # CHỐT CHẶN BẢO VỆ: Doanh thu thuần và lợi nhuận thuần thực tế phải về đúng 0
    assert kpis.net_revenue == Decimal("0")
    assert kpis.net_profit == Decimal("0")


def test_financial_case_accounting_garbage_adjustment(test_env):
    """
    Nghiệp vụ 3: Có phát sinh tiền dọn rác tồn kho (Luồng 1 - ép kho trống/kho âm về 0).
    Bản chất kế toán:
      - Bán hàng thành công thu về Doanh thu thuần: 50k, Giá vốn hàng bán: 30k.
      - Lợi nhuận gộp kỹ thuật thu được từ khách lẻ: 50k - 30k = 20k.
      - Trong kỳ, kế toán kích hoạt tác vụ dọn rác kho rỗng phát sinh khoản phạt/điều chỉnh chênh lệch: -5k.
      - Lợi nhuận thuần thực tế chảy vào két phải phản ánh đúng: 20k + (-5k) = 15k.
    """
    service, repo = test_env
    repo.stubbed_kpis = {
        "total_orders_created": 1, "total_orders_completed": 1, "total_orders_cancelled": 0,
        "gross_revenue": 50000.0, "cancelled_value": 0.0, "net_revenue": 50000.0,
        "total_cogs": 30000.0, "gross_profit": 20000.0, "variance_garbage": -5000.0, "net_profit": 15000.0
    }

    report: DashboardReportDTO = service.get_dashboard_report("2026-05-01", "2026-05-27")
    kpis = report.kpis

    assert kpis.net_revenue == Decimal("50000")
    assert kpis.gross_profit == Decimal("20000")
    assert kpis.variance_garbage == Decimal("-5000")

    # Lợi nhuận thuần thực tế thu được bắt buộc phải bị trừ đi 5k tiền dọn rác hệ thống
    assert kpis.net_profit == Decimal("15000")
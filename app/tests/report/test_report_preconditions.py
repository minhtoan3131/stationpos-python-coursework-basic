import pytest
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl


# ==========================================
# SETUP FAKE REPOSITORY & UOW (BỘ NHỚ RAM)
# ==========================================
class FakeReportRepository:
    """Fake Repo trống để đảm bảo code sẽ không bị sập vì thiếu hàm."""

    def get_kpi_metrics(self, start_date: str, end_date: str): return {}

    def get_revenue_trend(self, start_date: str, end_date: str): return []

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5): return []

    def get_transaction_history(self, start_date: str, end_date: str): return []

    def get_inventory_valuation(self): return []


class FakeUnitOfWork:
    """Giả lập Context Manager kết nối Database trên RAM"""

    def __init__(self):
        self.report_repo = FakeReportRepository()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ==========================================
# FIXTURE KHỞI TẠO SERVICE
# ==========================================
@pytest.fixture
def report_service():
    """Khởi tạo ReportServiceImpl sử dụng Fake UOW, không dùng Mock framework"""
    uow_factory = lambda: FakeUnitOfWork()
    return ReportServiceImpl(uow_factory)


# ==========================================
# DATA-DRIVEN TEST CASES (PARAMETRIZE)
# ==========================================
@pytest.mark.parametrize("scenario, start_date, end_date, expected_error_msg", [
    # --- TC_Pre_01: Sai định dạng hoặc chuỗi rỗng ---
    ("Start date trống", "", "2026-05-16", "định dạng"),
    ("End date trống", "2026-05-16", "", "định dạng"),
    ("Start date sai định dạng VN", "27/10/2023", "2026-05-16", "định dạng"),
    ("End date chứa cả giờ", "2026-05-16", "2026-05-16 23:59:59", "định dạng"),
    ("Dữ liệu ngày là chữ rác", "invalid-date", "2026-05-16", "định dạng"),

    # --- TC_Pre_02: Logic thời gian đảo lộn ---
    ("Ngày bắt đầu lớn hơn ngày kết thúc", "2026-05-17", "2026-05-16", "không được lớn hơn"),
])
def test_get_dashboard_report_preconditions_fail(report_service, scenario, start_date, end_date, expected_error_msg):
    """
    Vét cạn toàn bộ kịch bản lỗi đầu vào của hàm cửa ngõ.
    Tấm khiên bảo vệ bắt buộc phải ném lỗi ValueError khi dữ liệu rác vượt biên.
    """
    # GIVEN & WHEN: Thực thi hành động gọi hàm với data lỗi
    # THEN: Sử dụng pytest.raises tương tự assertThrows của JUnit để bắt lỗi
    with pytest.raises(ValueError) as exc_info:
        report_service.get_dashboard_report(start_date, end_date)

    # Kiểm chứng thông báo lỗi bắn ra phải chứa từ khóa cảnh báo tương ứng
    assert expected_error_msg in str(exc_info.value).lower()
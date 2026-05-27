# File: app/tests/report/test_report_preconditions.py
import pytest
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl
from app.core.exceptions.validation_exception import ValidationException # <--- ĐỒNG BỘ EXCEPTION MỚI


class FakeReportRepository:
    def get_kpi_metrics(self, start_date: str, end_date: str): return {}
    def get_revenue_trend(self, start_date: str, end_date: str): return []
    def get_top_products(self, start_date: str, end_date: str, limit: int = 5): return []
    def get_transaction_history(self, start_date: str, end_date: str): return []
    def get_inventory_valuation(self): return []


class FakeUnitOfWork:
    def __init__(self):
        self.report_repo = FakeReportRepository()
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def report_service():
    uow_factory = lambda: FakeUnitOfWork()
    return ReportServiceImpl(uow_factory)


@pytest.mark.parametrize("scenario, start_date, end_date, expected_error_msg", [
    # --- TC_Pre_01: Sai định dạng hoặc chuỗi rỗng ---
    ("Start date trống", "", "2026-05-16", "định dạng ngày bộ lọc không hợp lệ"),
    ("End date trống", "2026-05-16", "", "định dạng ngày bộ lọc không hợp lệ"),
    ("Start date sai định dạng VN", "27/10/2023", "2026-05-16", "định dạng ngày bộ lọc không hợp lệ"),
    ("End date chứa cả giờ", "2026-05-16", "2026-05-16 23:59:59", "định dạng ngày bộ lọc không hợp lệ"),
    ("Dữ liệu ngày là chữ rác", "invalid-date", "2026-05-16", "định dạng ngày bộ lọc không hợp lệ"),

    # --- TC_Pre_02: Logic thời gian đảo lộn ---
    ("Ngày bắt đầu lớn hơn ngày kết thúc", "2026-05-17", "2026-05-16", "không được lớn hơn ngày kết thúc"),
])
def test_get_dashboard_report_preconditions_fail(report_service, scenario, start_date, end_date, expected_error_msg):
    """Kiểm toán chốt chặn đầu vào: Bắt buộc quăng ValidationException thay vì lỗi ValueError hệ thống"""
    with pytest.raises(ValidationException) as exc_info:
        report_service.get_dashboard_report(start_date, end_date)

    assert expected_error_msg in str(exc_info.value).lower()
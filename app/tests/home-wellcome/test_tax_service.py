import pytest
from decimal import Decimal
from app.modules.tax.services.impl.tax_service_impl import TaxService


# =========================================================================
# FIXTURES
# =========================================================================
@pytest.fixture
def tax_service(mocker):
    """
    Mock UnitOfWork cho TaxService
    """
    mock_uow = mocker.MagicMock()
    mock_uow.__enter__.return_value = mock_uow
    mock_uow_factory = mocker.MagicMock(return_value=mock_uow)

    service = TaxService(mock_uow_factory)
    return service, mock_uow


# =========================================================================
# TEST CASES
# =========================================================================
def test_get_tax_warning_status_triggers_at_85_percent(tax_service, mocker):
    """
    Kiểm tra Post-condition: Khi doanh thu chạm ngưỡng 85% của mức miễn thuế,
    cờ is_near_threshold bắt buộc phải bật thành True.
    """
    service, mock_uow = tax_service

    # 1. GIVEN: Giả lập Database trả về thông tin thuế

    # - Mock cấu hình Thuế: Ngưỡng (Threshold) = 1 Tỷ (1,000,000,000)
    mock_config = mocker.MagicMock()
    mock_config.threshold_amount = Decimal('1000000000')
    mock_config.vat_percent = Decimal('1.0')
    mock_config.pit_percent = Decimal('0.5')
    mock_uow.tax_config_repo.get_config_by_year.return_value = mock_config

    # - Mock Doanh thu thực tế: Revenue = 850 Triệu (850,000,000)
    mock_revenue = mocker.MagicMock()
    mock_revenue.month = 5
    mock_revenue.revenue = Decimal('850000000')
    mock_uow.tax_report_repo.get_monthly_revenue_by_year.return_value = [mock_revenue]

    # 2. WHEN: Kích hoạt hàm kiểm tra trạng thái cảnh báo
    status = service.get_tax_warning_status(2026)

    # 3. THEN: Kiểm tra các phép toán nghiệp vụ
    assert status['threshold'] == 1000000000.0, "Ngưỡng trả về phải đúng 1 Tỷ"
    assert status['revenue'] == 850000000.0, "Doanh thu trả về phải đúng 850 Triệu"

    # - Phép tính % phải đúng 85.0
    assert status['percent'] == 85.0

    # - Cờ cảnh báo phải bật
    assert status['is_near_threshold'] is True, "Cờ cảnh báo phải bật (True) khi chạm 85%"
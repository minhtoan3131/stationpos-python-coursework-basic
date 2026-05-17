import pytest
import datetime
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl


# =========================================================================
# FIXTURES
# =========================================================================
@pytest.fixture
def report_service(mocker):
    """
    Khởi tạo ReportService và làm giả (Mock) UnitOfWork (uow).
    """
    # Làm giả context manager (khối 'with self.uow_factory() as uow')
    mock_uow = mocker.MagicMock()
    mock_uow.__enter__.return_value = mock_uow
    mock_uow_factory = mocker.MagicMock(return_value=mock_uow)

    service = ReportServiceImpl(mock_uow_factory)
    return service, mock_uow


# =========================================================================
# TEST CASES
# =========================================================================
def test_get_daily_activity_feed_merges_and_sorts_correctly(report_service):
    """
    Kiểm tra Post-condition: Dữ liệu (Bán hàng và Nhập kho) phải được gộp
    và sắp xếp theo thứ tự giảm dần của thời gian (Mới nhất lên đầu).
    """
    service, mock_uow = report_service

    # 1. GIVEN: Giả lập dữ liệu thô từ Database (Repo)
    # Giả lập Repo bán hàng trả về 1 Hóa đơn lúc 10:00 sáng
    mock_uow.report_repo.get_transaction_history.return_value = [
        {
            'invoice_code': 'HD-001',
            'created_at': '2026-05-17 10:00',  # Trả về chuỗi
            'final_amount': 500000,
            'payment_method': 'Tiền mặt'
        }
    ]

    # Giả lập Repo nhập kho trả về 1 Phiếu nhập lúc 14:00 chiều
    mock_uow.report_repo.get_daily_purchase_orders.return_value = [
        {
            'code': 'PN-001',
            'created_at': datetime.datetime(2026, 5, 17, 14, 0),  # Trả về datetime object
            'total_amount': 1500000,
            'supplier_name': 'NCC Thiên Long'
        }
    ]

    # 2. WHEN: Gọi hàm nghiệp vụ tổng hợp luồng hoạt động
    feed_result = service.get_daily_activity_feed('2026-05-17')

    # 3. THEN: Kiểm tra các điều kiện hậu quyết (Post-conditions)
    # - Mảng phải có đúng 2 phần tử
    assert len(feed_result) == 2, "Hàm phải gộp được cả 2 luồng dữ liệu"

    # - Phần tử đầu tiên (Mới nhất - 14:00) PHẢI LÀ Phiếu nhập kho (IMPORT)
    assert feed_result[0]['type'] == 'IMPORT'
    assert feed_result[0]['code'] == 'PN-001'
    assert feed_result[0]['created_at'] == '2026-05-17 14:00'

    # - Phần tử thứ hai (Cũ hơn - 10:00) PHẢI LÀ Hóa đơn bán hàng (SALE)
    assert feed_result[1]['type'] == 'SALE'
    assert feed_result[1]['code'] == 'HD-001'
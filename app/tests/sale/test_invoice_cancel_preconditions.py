import pytest
from datetime import datetime
from decimal import Decimal
from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl
from app.core.exceptions.validation_exception import ValidationException

# ==========================================
# SETUP FAKE REPOSITORIES (PRECONDITIONS)
# ==========================================
class FakeInvoiceHistoryRepository:
    def __init__(self):
        self.mock_metadata = {
            "HD-001": {'id': 1, 'code': 'HD-001', 'status': 'COMPLETED', 'created_at': datetime.now()},
            "HD-002": {'id': 2, 'code': 'HD-002', 'status': 'CANCELLED', 'created_at': datetime.now()}
        }

    def fetch_invoice_metadata(self, invoice_code: str) -> dict:
        return self.mock_metadata.get(invoice_code)

    def fetch_invoice_details(self, invoice_code: str) -> list:
        if invoice_code == "HD-001":
            return [{'product_id': 100, 'quantity': 5, 'total_cogs_amount': Decimal('20000.0000')}]
        return []

class FakeUnitOfWork:
    def __init__(self):
        self.invoice_history_repo = FakeInvoiceHistoryRepository()
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

@pytest.fixture
def history_service():
    return InvoiceHistoryServiceImpl(lambda: FakeUnitOfWork())

# ==========================================
# PARAMETRIZE VÉT CẠN CÁC CHỐT CHẶN BƯỚC 1
# ==========================================
@pytest.mark.parametrize("invoice_code, reason, expected_error_msg", [
    ("HD-001", "", "Vui lòng cung cấp lý do hủy hóa đơn."),
    ("HD-001", "   ", "Vui lòng cung cấp lý do hủy hóa đơn."),
    ("HD-999", "Nhầm lẫn", "Không tìm thấy hóa đơn yêu cầu."),
    ("HD-002", "Hủy lại", "Hóa đơn này đã được hủy trước đó."),
])
def test_cancel_invoice_preconditions_fails(history_service, invoice_code, reason, expected_error_msg):
    """Kiểm toán Bước 1: Ngăn chặn và quăng ValidationException nếu vi phạm chốt chặn đầu vào"""
    with pytest.raises(ValidationException) as exc_info:
        history_service.execute_cancel_invoice(invoice_code, reason)
    assert expected_error_msg in str(exc_info.value)
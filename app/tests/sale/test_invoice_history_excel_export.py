import pytest
import os
from datetime import datetime
from decimal import Decimal
from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl


# ==========================================
# SETUP FAKE REPOSITORIES & UOW CHUYÊN BIỆT
# ==========================================
class FakeInvoiceHistoryRepository:
    def fetch_invoice_metadata(self, invoice_code: str) -> dict:
        # Trả về thông tin Header mẫu khớp chuẩn với schema hạch toán
        return {
            'id': 88,
            'code': 'HD-20260527-085900-421',
            'created_at': datetime.now(),
            'total_amount': Decimal('150000.0000'),
            'discount': Decimal('0.0000'),
            'final_amount': Decimal('150000.0000'),
            'payment_method': 'CASH',
            'cash_received': Decimal('200000.0000'),
            'status': 'COMPLETED',
            'cancel_reason': None
        }

    def fetch_invoice_details(self, invoice_code: str) -> list:
        # Trả về danh sách chi tiết mặt hàng mồi
        return [
            {
                'product_id': 100,
                'unit_id': 10,
                'sku': 'SP01',
                'product_name': 'Bút bi Thiên Long',
                'unit_name': 'Cái',
                'quantity': 5,
                'unit_price': Decimal('10000.0000'),
                'total_price': Decimal('50000.0000')
            },
            {
                'product_id': 101,
                'unit_id': 10,
                'sku': 'SP02',
                'product_name': 'Thước kẻ Milan',
                'unit_name': 'Cái',
                'quantity': 5,
                'unit_price': Decimal('20000.0000'),
                'total_price': Decimal('100000.0000')
            }
        ]


class FakeUnitOfWork:
    def __init__(self):
        self.invoice_history_repo = FakeInvoiceHistoryRepository()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ==========================================
# FIXTURE KHỞI TẠO HISTORY SERVICE
# ==========================================
@pytest.fixture
def invoice_history_service():
    return InvoiceHistoryServiceImpl(lambda: FakeUnitOfWork())


# ==========================================
# BỘ BÀI TEST CASES CHÍNH THỨC
# ==========================================

def test_export_invoice_excel_success_with_tmp_path(invoice_history_service, tmp_path):
    """TC_Excel_01: Xuất file Excel chi tiết hóa đơn thành công không để lại rác tàn dư"""
    from app.modules.sale.utils.invoice_history_excel_exporter import InvoiceHistoryExcelExporter

    # 1. GIVEN: Sinh đường dẫn tệp ảo cô lập do Pytest quản lý vòng đời
    export_file = tmp_path / "HoaDon_HD-20260527-085900-421.xlsx"

    # Lấy cấu trúc cục dữ liệu thô từ Service hệt như luồng chạy của UI Controller
    raw_data = invoice_history_service.export_invoice_to_excel("HD-20260527-085900-421")

    # 2. WHEN: Gọi Exporter đẩy luồng dữ liệu xuống ổ đĩa
    result = InvoiceHistoryExcelExporter.export_detail(
        file_path=str(export_file),
        metadata=raw_data['metadata'],
        items=raw_data['items']
    )

    # 3. THEN: Kiểm chứng kết quả kết xuất
    # - Hàm kết xuất bắt buộc phải trả về dấu hiệu thành công (True)
    assert result is True
    # - Tệp tin Excel vật lý thực sự được khởi tạo và tồn tại trong thư mục ảo (Chứng tỏ openpyxl đã biên dịch XML sạch)
    assert os.path.exists(export_file)


def test_export_invoice_excel_throws_error_on_forbidden_path(invoice_history_service):
    """TC_Excel_02: Trình xuất lỗi hệ thống khi truyền đường dẫn cấm ghi hoặc không tồn tại"""
    from app.modules.sale.utils.invoice_history_excel_exporter import InvoiceHistoryExcelExporter

    # GIVEN: Một thư mục ma thuật hoàn toàn không có thực trên hệ điều hành
    invalid_path = "/thumu_ma_thuat_cam_ghi_he_thong/HoaDon.xlsx"
    raw_data = invoice_history_service.export_invoice_to_excel("HD-20260527-085900-421")

    # WHEN & THEN: Hệ thống phải bắt trọn Exception và quăng ra thông báo đóng gói rõ nghĩa
    with pytest.raises(Exception) as exc_info:
        InvoiceHistoryExcelExporter.export_detail(
            file_path=invalid_path,
            metadata=raw_data['metadata'],
            items=raw_data['items']
        )

    assert "Có lỗi khi xuất Excel chi tiết hóa đơn" in str(exc_info.value)
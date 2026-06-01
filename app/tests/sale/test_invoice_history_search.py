import pytest
from datetime import date, datetime
from decimal import Decimal


from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl
from app.modules.sale.ui.controllers.invoice_history_controller import InvoiceHistoryController


# ==========================================
# SETUP FAKE REPOSITORIES & UOW FOR SEARCH
# ==========================================
class FakeInvoiceHistoryRepository:
    def __init__(self):
        # Dữ liệu mồi giả lập bảng invoices trong CSDL
        self.mock_db_invoices = [
            {
                'code': 'HD-001', 'created_at': datetime(2026, 5, 10, 10, 0),
                'final_amount': Decimal('150000'), 'payment_method': 'CASH', 'status': 'COMPLETED'
            },
            {
                'code': 'HD-002', 'created_at': datetime(2026, 5, 15, 14, 30),
                'final_amount': Decimal('250000'), 'payment_method': 'TRANSFER', 'status': 'COMPLETED'
            },
            {
                'code': 'HD-003', 'created_at': datetime(2026, 5, 20, 9, 15),
                'final_amount': Decimal('90000'), 'payment_method': 'CASH', 'status': 'CANCELLED'
            }
        ]

    def fetch_invoices_master(self, keyword: str = None, date_from: date = None,
                              date_to: date = None, payment_method: str = None,
                              status: str = None) -> list:
        """Mô phỏng bộ lọc động phức tạp giống hệt SQL WHERE ở Repository thật"""
        filtered_results = []

        for inv in self.mock_db_invoices:
            inv_date = inv['created_at'].date()

            # 1. Lọc khoảng thời gian (Bắt buộc)
            if date_from and inv_date < date_from: continue
            if date_to and inv_date > date_to: continue

            # 2. Lọc theo Hình thức thanh toán (CASH / TRANSFER)
            if payment_method and inv['payment_method'] != payment_method: continue

            # 3. Lọc theo Trạng thái (COMPLETED / CANCELLED)
            if status and inv['status'] != status: continue

            # 4. Lọc theo Từ khóa (Mã hóa đơn)
            if keyword and keyword not in inv['code']: continue

            filtered_results.append(inv)

        return filtered_results


class FakeUnitOfWork:
    def __init__(self):
        self.invoice_history_repo = FakeInvoiceHistoryRepository()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES KHỞI TẠO TẦNG LÕI & GIAO DIỆN
# ==========================================
@pytest.fixture
def history_service():
    """Khởi tạo Service độc lập gắn kèm Fake UOW"""
    return InvoiceHistoryServiceImpl(lambda: FakeUnitOfWork())


@pytest.fixture
def mock_ui_components(mocker):
    """Làm giả các Sub-widgets trên giao diện Qt để test Controller cô lập"""
    ui = mocker.Mock()

    # Giả lập các ô nhập liệu bộ lọc thời gian
    ui.date_invoice_from = mocker.Mock()
    ui.date_invoice_to = mocker.Mock()
    ui.txt_search_invoice = mocker.Mock()

    # Giả lập các hộp chọn ComboBox
    ui.cbo_payment_method_filter = mocker.Mock()
    ui.cbo_status_invoice = mocker.Mock()

    # Giả lập bảng danh sách và khung splitter hiển thị
    ui.tbl_invoice_master = mocker.Mock()
    ui.tbl_invoice_details = mocker.Mock()
    ui.splitter_invoice = mocker.Mock()

    # Giả lập các Label tiền và metadata
    ui.lbl_md_invoice_id = mocker.Mock()
    ui.lbl_md_invoice_date = mocker.Mock()
    ui.lbl_md_invoice_status = mocker.Mock()
    ui.lbl_detail_total_value = mocker.Mock()
    ui.lbl_detail_cash_received_label = mocker.Mock()
    ui.btn_cancel_invoice = mocker.Mock()

    return ui


# ==========================================
#  UNIT TEST CHO BỘ LỌC PHỨC TẠP (SERVICE LAYER)
# ==========================================

@pytest.mark.parametrize("filters, expected_count, first_code", [
    # Kịch bản 1: Chỉ lọc ngày, lấy toàn bộ danh sách trong tháng 5
    ({"date_from": date(2026, 5, 1), "date_to": date(2026, 5, 31)}, 3, "HD-001"),

    # Kịch bản 2: Lọc khoảng ngày không có dữ liệu phát sinh
    ({"date_from": date(2026, 6, 1), "date_to": date(2026, 6, 30)}, 0, None),

    # Kịch bản 3: Tổ hợp phức tạp - Lọc Tiền mặt (CASH) + Đã hoàn thành (COMPLETED)
    ({"date_from": date(2026, 5, 1), "date_to": date(2026, 5, 31), "payment_method": "CASH", "status": "COMPLETED"}, 1,
     "HD-001"),

    # Kịch bản 4: Tổ hợp phức tạp - Lọc Tiền mặt (CASH) + Trạng thái Đã hủy (CANCELLED)
    ({"date_from": date(2026, 5, 1), "date_to": date(2026, 5, 31), "payment_method": "CASH", "status": "CANCELLED"}, 1,
     "HD-003"),

    # Kịch bản 5: Tìm kiếm chính xác theo Mã từ khóa hóa đơn
    ({"date_from": date(2026, 5, 1), "date_to": date(2026, 5, 31), "keyword": "HD-002"}, 1, "HD-002"),
])
def test_service_search_invoices_with_complex_combinatorial_filters(history_service, filters, expected_count,
                                                                    first_code):
    """Kiểm toán tầng Service: Đảm bảo bộ lọc logic rẽ nhánh động hạch toán chính xác số lượng bản ghi"""
    results = history_service.search_invoices(filters)

    assert len(results) == expected_count
    if expected_count > 0:
        assert results[0]['code'] == first_code


# ==========================================
# UI CONTROLLER TEST (MOCKING & STATE CORRELATION)
# ==========================================

def test_controller_load_master_data_extracts_ui_states_correctly(mock_ui_components, mocker):
    """Kiểm toán tầng UI: Đảm bảo Controller đọc đúng chỉ mục ComboBox và map sang chuỗi ENUM Database"""
    # 1. GIVEN: Giả lập kế toán chọn bộ lọc phức tạp trên màn hình:
    # Chọn "Chuyển khoản" (Index 2) và chọn trạng thái "Đã hủy" (Index 2)
    mock_ui_components.txt_search_invoice.text.return_value = "  HD-002  "
    mock_ui_components.date_invoice_from.date.return_value.toPyDate.return_value = date(2026, 5, 1)
    mock_ui_components.date_invoice_to.date.return_value.toPyDate.return_value = date(2026, 5, 31)

    mock_ui_components.cbo_payment_method_filter.currentIndex.return_value = 2  # Chuyển khoản
    mock_ui_components.cbo_status_invoice.currentIndex.return_value = 2  # Đã hủy

    # Làm giả lời gọi hàm xử lý của Service
    spy_service = mocker.Mock()
    spy_service.search_invoices.return_value = []

    controller = InvoiceHistoryController(mock_ui_components, spy_service)

    # 2. WHEN: Kích hoạt lệnh nạp và tìm kiếm dữ liệu
    controller.load_master_data()

    # 3. THEN: Khẳng định Controller đã bóc tách chuỗi, loại bỏ khoảng trắng và chuyển đổi text index chính xác
    spy_service.search_invoices.assert_called_once_with({
        "keyword": "HD-002",
        "date_from": date(2026, 5, 1),
        "date_to": date(2026, 5, 31),
        "payment_method": "TRANSFER",  # Bắt buộc chuyển sang chữ hoa khớp Schema
        "status": "CANCELLED"  # Bắt buộc chuyển sang chữ hoa khớp Schema
    })


def test_controller_handle_reset_filters_restores_default_dates_and_reloads(mock_ui_components, mocker):
    """Kiểm toán giao diện: Bấm Làm mới phải trả ngày về đầu tháng, dọn sạch ô text và nạp lại DB"""
    spy_service = mocker.Mock()
    spy_service.search_invoices.return_value = []

    controller = InvoiceHistoryController(mock_ui_components, spy_service)

    spy_set_date_from = mock_ui_components.date_invoice_from.setDate
    spy_set_date_to = mock_ui_components.date_invoice_to.setDate
    spy_clear_text = mock_ui_components.txt_search_invoice.clear
    spy_reset_cbo_1 = mock_ui_components.cbo_payment_method_filter.setCurrentIndex
    spy_reset_cbo_2 = mock_ui_components.cbo_status_invoice.setCurrentIndex

    spy_set_date_from.reset_mock()
    spy_set_date_to.reset_mock()
    spy_clear_text.reset_mock()
    spy_reset_cbo_1.reset_mock()
    spy_reset_cbo_2.reset_mock()
    spy_service.search_invoices.reset_mock()

    # WHEN: Kích hoạt sự kiện bấm nút "Làm Mới" thực tế của người dùng
    controller.handle_reset_filters()

    # THEN: Xác minh toàn bộ các trường nhập liệu bị cưỡng bức về trạng thái ban đầu trọn vẹn 1 lần bấm
    spy_set_date_from.assert_called_once_with(mocker.ANY)
    spy_set_date_to.assert_called_once_with(mocker.ANY)
    spy_clear_text.assert_called_once()
    spy_reset_cbo_1.assert_called_once_with(0)
    spy_reset_cbo_2.assert_called_once_with(0)

    # Hệ thống bắt buộc phải tự động gọi lại hàm nạp danh sách ngay sau đó
    spy_service.search_invoices.assert_called_once()
import pytest
from decimal import Decimal
from PyQt6.QtCore import Qt

from app.modules.sale.ui.controllers.checkout_dialog_controller import CheckoutDialogController
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO


# ==========================================
# 1. FIXTURE KHỞI TẠO DỮ LIỆU & GIAO DIỆN
# ==========================================
@pytest.fixture
def sample_checkout_dto():
    """Tạo DTO mồi mô phỏng giỏ hàng được truyền từ màn hình chính sang"""
    items = [
        CartItemDTO(product_id=1, sku="SP01", name="Bút bi", unit_id=10, unit_name="Cái",
                    quantity=5, price=Decimal('10000'), total=Decimal('50000'), cost_price=Decimal('4000'))
    ]
    return CheckoutDTO(
        code="",  # Cố tình để trống để test logic tự sinh mã
        total_amount=Decimal('50000'),
        discount=Decimal('0'),
        final_amount=Decimal('50000'),
        payment_method='CASH',
        cash_received=Decimal('0'),
        items=items
    )


@pytest.fixture
def checkout_dialog(qtbot, sample_checkout_dto):
    dialog = CheckoutDialogController(checkout_dto=sample_checkout_dto)
    qtbot.addWidget(dialog)
    return dialog


# ==========================================
# LUỒNG HIỂN THỊ DỮ LIỆU BAN ĐẦU
# ==========================================
def test_should_populate_invoice_data_and_generate_code_when_dialog_initializes(checkout_dialog):
    """Khi mở hộp thoại: Phải tự sinh mã HĐ, nạp đúng tổng tiền và hiển thị chi tiết giỏ hàng"""
    dialog = checkout_dialog

    # Mã HĐ phải được tự động sinh (Bắt đầu bằng HD-)
    assert dialog.checkout_dto.code.startswith("HD-")
    assert dialog.ui.lbl_invoice_id.text() == f"Số HĐ: {dialog.checkout_dto.code}"

    # Tổng tiền phải chuẩn
    assert dialog.ui.lbl_grand_total.text() == "50,000 VND"

    # Bảng chi tiết phải có dữ liệu
    assert dialog.ui.tbl_invoice_items.rowCount() == 1
    assert dialog.ui.tbl_invoice_items.item(0, 0).text() == "Bút bi"

    # Mặc định tiền khách đưa = tiền hóa đơn
    assert dialog.ui.spn_cash_received.value() == 50000.0


# ==========================================
# LUỒNG THAY ĐỔI PHƯƠNG THỨC THANH TOÁN
# ==========================================
def test_should_disable_cash_input_and_reset_change_when_payment_method_is_transfer(checkout_dialog):
    """Nếu chọn Chuyển khoản: Khóa ô nhập tiền, tự điền đủ tiền và cho tiền thừa về 0"""
    dialog = checkout_dialog

    # Đổi sang index 1 (Chuyển khoản / Quẹt thẻ)
    dialog.ui.cbo_payment_method.setCurrentIndex(1)

    assert dialog.ui.spn_cash_received.isEnabled() is False
    assert dialog.ui.spn_cash_received.value() == 50000.0
    assert dialog.ui.lbl_change_due.text() == "0 VND"


def test_should_enable_cash_input_when_payment_method_switched_back_to_cash(checkout_dialog):
    """Chuyển lại Tiền mặt thì phải mở khóa ô nhập tiền"""
    dialog = checkout_dialog

    # Chuyển khoản -> Tiền mặt
    dialog.ui.cbo_payment_method.setCurrentIndex(1)
    dialog.ui.cbo_payment_method.setCurrentIndex(0)

    assert dialog.ui.spn_cash_received.isEnabled() is True


# ==========================================
# LUỒNG TÍNH TOÁN TIỀN THỪA (REAL-TIME)
# ==========================================
def test_should_calculate_correct_change_and_display_green_text_when_cash_is_sufficient(checkout_dialog):
    """Nhập số tiền > tổng tiền: Tính đúng tiền thừa và hiển thị chữ màu xanh"""
    dialog = checkout_dialog

    # Khách đưa 100k
    dialog.ui.spn_cash_received.setValue(100000.0)

    # Trả lại 50k
    assert dialog.ui.lbl_change_due.text() == "50,000 VND"
    assert "#10b981" in dialog.ui.lbl_change_due.styleSheet()  # Mã màu xanh lá


def test_should_display_warning_and_red_text_when_cash_is_insufficient(checkout_dialog):
    """Nhập số tiền < tổng tiền: Hiện chữ 'Khách đưa chưa đủ!' màu đỏ"""
    dialog = checkout_dialog

    # Khách đưa 30k
    dialog.ui.spn_cash_received.setValue(30000.0)

    assert dialog.ui.lbl_change_due.text() == "Khách đưa chưa đủ!"
    assert "#ef4444" in dialog.ui.lbl_change_due.styleSheet()  # Mã màu đỏ


# ==========================================
# LUỒNG BẤM XÁC NHẬN (CONFIRM)
# ==========================================
def test_should_show_warning_and_prevent_confirmation_when_cash_is_insufficient(qtbot, checkout_dialog, mocker):
    """Bấm Xác nhận mà tiền mặt đưa thiếu -> Chặn lại, hiện cảnh báo, Dialog không được đóng"""
    dialog = checkout_dialog
    mock_warning = mocker.patch('app.modules.sale.ui.controllers.checkout_dialog_controller.QMessageBox.warning')
    mock_accept = mocker.patch.object(dialog, 'accept')

    # GIVEN: Tiền thiếu
    dialog.ui.spn_cash_received.setValue(30000.0)

    # WHEN: Bấm Xác nhận
    qtbot.mouseClick(dialog.ui.btn_confirm, Qt.MouseButton.LeftButton)

    # THEN: Bị chặn
    mock_warning.assert_called_once()
    mock_accept.assert_not_called()
    assert dialog.is_confirmed is False


def test_should_update_dto_and_accept_dialog_when_confirm_is_clicked_with_valid_payment(qtbot, checkout_dialog, mocker):
    """Bấm Xác nhận hợp lệ -> Cập nhật thông tin vào DTO gốc, đóng Dialog thành công"""
    dialog = checkout_dialog
    mock_accept = mocker.patch.object(dialog, 'accept')

    # GIVEN: Khách thanh toán bằng Chuyển khoản
    dialog.ui.cbo_payment_method.setCurrentIndex(1)

    # WHEN: Bấm Xác nhận
    qtbot.mouseClick(dialog.ui.btn_confirm, Qt.MouseButton.LeftButton)

    # THEN: Hoàn tất
    mock_accept.assert_called_once()
    assert dialog.is_confirmed is True

    # DTO phải được chuẩn hóa đúng trước khi gửi về Controller chính
    assert dialog.checkout_dto.payment_method == 'TRANSFER'
    assert dialog.checkout_dto.cash_received == Decimal('50000')
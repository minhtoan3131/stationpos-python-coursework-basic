import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QSpinBox

from app.modules.sale.ui.controllers.sales_management_controller import SalesManagementController
from app.modules.sale.ui.controllers.checkout_dialog_controller import CheckoutDialogController
from app.modules.sale.dtos.sale_dto import CheckoutDTO


@pytest.fixture
def sale_window(qtbot, mocker):
    """Fixture nạp màn hình bán hàng POS giả lập hạ tầng lõi"""
    mock_inv_service = MagicMock()
    mock_prod_service = MagicMock()
    mock_sale_service = MagicMock()
    mock_hist_service = MagicMock()
    mock_cfg_service = MagicMock()

    window = SalesManagementController(
        inventory_service=mock_inv_service,
        product_service=mock_prod_service,
        sale_service=mock_sale_service,
        invoice_history_service=mock_hist_service,
        store_config_service=mock_cfg_service
    )
    qtbot.addWidget(window)
    return window


def test_sale_checkout_should_reject_when_total_exceeds_50_billion(sale_window, mocker):
    """
    CHỐT CHẶN POS: Tổng tiền hóa đơn giỏ hàng vượt quá 50 Tỷ VND trước khi mở màn hình tính tiền.
    Kỳ vọng: Báo lỗi critical, chặn đứng luồng thanh toán tại chỗ.
    """
    # GIVEN: Thiết lập giỏ hàng có 1 dòng vật lý chứa giá trị khủng để ép tổng tiền lên 60 Tỷ VND
    sale_window.ui.tbl_cart.setRowCount(1)

    sku_item = QTableWidgetItem("SP001")
    sku_item.setData(Qt.ItemDataRole.UserRole, 1)
    sale_window.ui.tbl_cart.setItem(0, 0, sku_item)  # Cột 0: SKU

    name_item = QTableWidgetItem("Sách Quý Khổng Lồ")
    name_item.setData(Qt.ItemDataRole.UserRole, 10000)  # cost_price ngầm
    sale_window.ui.tbl_cart.setItem(0, 1, name_item)  # Cột 1: Tên

    unit_item = QTableWidgetItem("Cuốn")
    unit_item.setData(Qt.ItemDataRole.UserRole, 1)
    sale_window.ui.tbl_cart.setItem(0, 2, unit_item)  # Cột 2: ĐVT

    spin_qty = QSpinBox()
    spin_qty.setValue(1)
    sale_window.ui.tbl_cart.setCellWidget(0, 3, spin_qty)  # Cột 3: Số lượng

    sale_window.ui.tbl_cart.setItem(0, 4, QTableWidgetItem("60,000,000,000"))  # Cột 4: Đơn giá
    sale_window.ui.tbl_cart.setItem(0, 5, QTableWidgetItem("60,000,000,000"))  # Cột 5: Thành tiền

    mock_critical = mocker.patch('PyQt6.QtWidgets.QMessageBox.critical')
    mock_dialog = mocker.patch('app.modules.sale.ui.controllers.sales_management_controller.CheckoutDialogController')

    # ACT: Thu ngân bấm nút tiến hành Thanh toán hóa đơn
    sale_window.handle_checkout()

    # THEN: Khống chế thành công, hiện dialog critical từ chối và chặn không mở form thanh toán con
    mock_critical.assert_called_once()
    assert "VƯỢT NGƯỠNG HẠN MỨC HỆ THỐNG" in mock_critical.call_args[0][2]
    mock_dialog.assert_not_called()


def test_checkout_dialog_should_have_maximum_cash_input_limit(qtbot):
    """
    CHỐT CHẶN DIALOG UI: Kiểm tra trần SpinBox tiền khách đưa.
    Kỳ vọng: Ô spn_cash_received phải được cấu hình nới rộng trần lên tối đa 100 Tỷ VND.
    """
    # GIVEN: Khởi dựng cửa sổ thanh toán con với hóa đơn mẫu 100k
    fake_dto = CheckoutDTO(
        code="HD001", total_amount=Decimal('100000'), discount=Decimal('0'),
        final_amount=Decimal('100000'), payment_method='CASH', cash_received=Decimal('100000'),
        items=[]
    )
    dialog = CheckoutDialogController(checkout_dto=fake_dto)
    qtbot.addWidget(dialog)

    # THEN: Xác minh ô nhập liệu tiền mặt không bị kẹt ở mức mặc định thấp mà cho gõ tới 100 Tỷ
    assert dialog.ui.spn_cash_received.maximum() == 100000000000.0


def test_checkout_dialog_confirm_should_reject_when_cash_received_exceeds_100_billion(qtbot, mocker):
    """
    CHỐT CHẶN DIALOG CONTROLLER: Thu ngân gõ nhầm số tiền mặt khách đưa vượt quá 100 Tỷ VND.
    Kỳ vọng: Đánh chặn cảnh báo gõ thừa số 0, khóa trạng thái xác nhận (is_confirmed = False).
    """
    # GIVEN: Mở dialog thanh toán lên với tổng đơn thực tế (200k)
    fake_dto = CheckoutDTO(
        code="HD002", total_amount=Decimal('200000'), discount=Decimal('0'),
        final_amount=Decimal('200000'), payment_method='CASH', cash_received=Decimal('200000'),
        items=[]
    )
    dialog = CheckoutDialogController(checkout_dto=fake_dto)
    qtbot.addWidget(dialog)

    # Ép ô nhập liệu mở rộng trần tối đa ngay trong môi trường Test
    # Điều này ngăn không cho Qt Designer tự động bóp nghẹt con số 120 Tỷ về giá trị mặc định nhỏ
    dialog.ui.spn_cash_received.setMaximum(200000000000.0) # Nới trần lên 200 Tỷ

    # Gõ nhầm nút: Khách đưa 200k nhưng gõ thừa số 0 thành 120 Tỷ VND vượt hạn mức an toàn
    dialog.ui.spn_cash_received.setValue(120000000000.0)
    mocker.patch.object(dialog.ui.cbo_payment_method, 'currentIndex', return_value=0) # Chọn: Tiền mặt

    mock_warning = mocker.patch('PyQt6.QtWidgets.QMessageBox.warning')

    # ACT: Nhấn nút hoàn thành hóa đơn
    dialog.handle_confirm()

    # THEN: Hệ thống gác cổng kích hoạt từ chối phê duyệt giao dịch ảo và quăng cảnh báo warning thành công
    mock_warning.assert_called_once()
    assert "vượt quá hạn mức thanh toán thực tế" in mock_warning.call_args[0][2]
    assert dialog.is_confirmed is False
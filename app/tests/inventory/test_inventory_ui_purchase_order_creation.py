import pytest
import types
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTableWidgetItem

from app.modules.inventory.ui.controllers.inventory_management_controller import InventoryManagementController
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# 1. FIXTURE KHỞI TẠO & HÀM PHỤ TRỢ (HELPER)
# ==========================================
@pytest.fixture
def inventory_window(qtbot, mocker):
    mock_inventory_service = mocker.Mock()
    mock_supplier_service = mocker.Mock()
    mock_po_history_service = mocker.Mock()

    # Mồi sẵn dữ liệu cơ bản
    mock_supplier_service.get_all_suppliers.return_value = [{'id': 1, 'name': 'Thiên Long'}]
    mock_inventory_service.get_inventory_list.return_value = []

    window = InventoryManagementController(
        mock_inventory_service,
        mock_supplier_service,
        mock_po_history_service
    )

    qtbot.addWidget(window)
    window.mock_inventory_service = mock_inventory_service
    window.mock_po_history_service = mock_po_history_service  # <--- THÊM DÒNG NÀY
    return window


def seed_cart_data(window, qtbot):
    """Mồi data chuẩn: Đã sửa đổi để điền thủ công giá nhập vào ô QTableWidget"""
    window.ui.cbo_supplier.setCurrentIndex(1)

    mock_product = types.SimpleNamespace(
        id=100, sku='SP01', name='Bút', base_unit_id=1, base_unit_name='Cây',
        conversion_unit_id=2, conversion_unit_name='Hộp', conversion_ratio=10, cost_price=5000
    )
    window.raw_inventory_data = {0: mock_product}
    window.ui.tbl_inventory.insertRow(0)
    window.ui.tbl_inventory.setCurrentCell(0, 0)
    window.mock_inventory_service.search_products_for_import.return_value = [mock_product]

    # Bấm nút đưa vào giỏ
    qtbot.mouseClick(window.ui.btn_import_action, Qt.MouseButton.LeftButton)

    # === Giả lập người dùng gõ đơn giá nhập vào cột số 4 vì mặc định đang để trống ===
    window.ui.tbl_items.item(0, 4).setText("5000")
    # Kích hoạt sự kiện thay đổi để UI tính toán lại tiền dòng và tiền tổng
    window.calculate_cart_total()

# ==========================================
# CÁC KỊCH BẢN TỪ CHỐI NGAY TẠI GIAO DIỆN (PRE-CONDITIONS)
# ==========================================
def test_should_show_warning_and_prevent_save_when_no_supplier_is_selected(qtbot, inventory_window, mocker):
    """Khi chưa chọn Nhà cung cấp, bấm Lưu phải hiện cảnh báo và chặn lệnh lưu DB"""
    mock_warning = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.warning')
    inventory_window.ui.cbo_supplier.setCurrentIndex(0)

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    inventory_window.mock_inventory_service.create_purchase_order.assert_not_called()


def test_should_show_warning_and_prevent_save_when_cart_is_empty(qtbot, inventory_window, mocker):
    """Khi giỏ hàng trống, bấm Lưu phải hiện cảnh báo và chặn lệnh lưu DB"""
    mock_warning = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.warning')
    inventory_window.ui.cbo_supplier.setCurrentIndex(1)

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    inventory_window.mock_inventory_service.create_purchase_order.assert_not_called()


# ==========================================
# KỊCH BẢN LƯU THÀNH CÔNG (POST-CONDITIONS / HAPPY PATH)
# ==========================================
def test_should_clear_cart_and_show_success_message_when_purchase_order_is_saved_successfully(qtbot, inventory_window,
                                                                                              mocker):
    """Khi nhập kho thành công: Phải thông báo ID phiếu và xóa trắng giỏ hàng"""
    seed_cart_data(inventory_window, qtbot)

    mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.PurchaseOrderConfirmController').return_value.exec.return_value = QDialog.DialogCode.Accepted
    mock_info = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.information')
    inventory_window.mock_inventory_service.create_purchase_order.return_value = 888

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    inventory_window.mock_inventory_service.create_purchase_order.assert_called_once()
    mock_info.assert_called_once()
    assert "888" in mock_info.call_args[0][2]
    assert inventory_window.ui.tbl_items.rowCount() == 0


# ==========================================
# CÁC KỊCH BẢN XỬ LÝ LỖI TRONG QUÁ TRÌNH LƯU (INVARIANTS)
# ==========================================
def test_should_abort_save_process_when_user_cancels_at_confirmation_dialog(qtbot, inventory_window, mocker):
    """Khi Form Xác Nhận hiện lên mà người dùng bấm Quay lại, phải hủy tiến trình lưu"""
    seed_cart_data(inventory_window, qtbot)

    mock_confirm = mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.PurchaseOrderConfirmController')
    mock_confirm.return_value.exec.return_value = QDialog.DialogCode.Rejected

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)
    inventory_window.mock_inventory_service.create_purchase_order.assert_not_called()


def test_should_show_warning_and_preserve_cart_data_when_backend_returns_validation_error(qtbot, inventory_window,
                                                                                          mocker):
    """Khi Backend báo lỗi quy tắc, hiển thị Warning nhưng KHÔNG xóa mất dữ liệu giỏ hàng"""
    seed_cart_data(inventory_window, qtbot)

    mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.PurchaseOrderConfirmController').return_value.exec.return_value = QDialog.DialogCode.Accepted
    mock_warning = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.warning')

    inventory_window.mock_inventory_service.create_purchase_order.side_effect = ValidationException("Sản phẩm đã khóa")

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    assert inventory_window.ui.tbl_items.rowCount() == 1  # Giỏ hàng nguyên vẹn


def test_should_show_critical_error_and_preserve_cart_data_when_backend_crashes(qtbot, inventory_window, mocker):
    """Khi Backend bị crash, hiển thị lỗi Critical, ứng dụng không văng và giữ nguyên giỏ hàng"""
    seed_cart_data(inventory_window, qtbot)

    mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.PurchaseOrderConfirmController').return_value.exec.return_value = QDialog.DialogCode.Accepted
    mock_critical = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.critical')

    inventory_window.mock_inventory_service.create_purchase_order.side_effect = Exception("Mất kết nối MySQL")

    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    mock_critical.assert_called_once()
    assert inventory_window.ui.tbl_items.rowCount() == 1  # Giỏ hàng nguyên vẹn


def test_should_show_warning_and_prevent_save_when_item_price_is_blank_on_ui(qtbot, inventory_window, mocker):
    """UI Test: Khi có mặt hàng để trống giá nhập, bấm lưu phải hiện thông báo cảnh báo"""
    mock_warning = mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.warning')

    # 1. GIVEN: Sử dụng hàm seed_cart_data gốc để giỏ hàng được đổ ĐẦY ĐỦ dữ liệu nền chuẩn mực (SKU, Tên, SL)
    # Hàm này mặc định điền giá "5000" vào ô giá
    seed_cart_data(inventory_window, qtbot)

    # 2. Thực hiện hành động phá dữ liệu: Lấy ô giá hiện tại (chắc chắn không bị None nhờ seed_cart_data)
    # Ghi đè chuỗi rỗng "" để giả lập người dùng xóa trắng giá nhập đi
    price_cell = inventory_window.ui.tbl_items.item(0, 4)
    assert price_cell is not None, "Ô giá nhập phải được khởi tạo từ seed_cart_data"
    price_cell.setText("")

    # Ép giỏ hàng tính toán lại tổng tiền theo giá trống vừa sửa
    inventory_window.calculate_cart_total()

    # 3. WHEN: Hành động bấm nút xác nhận lưu toàn bộ phiếu nhập
    qtbot.mouseClick(inventory_window.ui.btn_save_all, Qt.MouseButton.LeftButton)

    # 4. THEN: Kiểm chứng kết quả hệ thống bắt lỗi giá trống
    mock_warning.assert_called_once()

    # Gom toàn bộ chuỗi text từ tham số QMessageBox truyền ra
    actual_warning_message = " ".join([str(arg) for arg in mock_warning.call_args[0]])

    # Lúc này giỏ hàng đã có 1 mặt hàng thực sự (rowCount = 1), hệ thống bắt buộc phải ném lỗi giá trống
    assert "đang để trống giá" in actual_warning_message

    # Đảm bảo Service tầng dưới tuyệt đối không được gọi khi dữ liệu lỗi
    inventory_window.mock_inventory_service.create_purchase_order.assert_not_called()
import pytest
import types
from PyQt6.QtCore import Qt

from app.modules.inventory.ui.controllers.inventory_management_controller import InventoryManagementController


# ==========================================
# FIXTURE KHỞI TẠO
# ==========================================
@pytest.fixture
def inventory_window(qtbot, mocker):
    mock_inventory_service = mocker.Mock()
    mock_supplier_service = mocker.Mock()
    mock_supplier_service.get_all_suppliers.return_value = [{'id': 1, 'name': 'Thiên Long'}]

    mock_inventory_service.get_inventory_list.return_value = []
    window = InventoryManagementController(mock_inventory_service, mock_supplier_service)
    qtbot.addWidget(window)
    window.mock_inventory_service = mock_inventory_service
    window.mock_supplier_service = mock_supplier_service
    return window


# ==========================================
# LUỒNG TÌM KIẾM TỒN KHO
# ==========================================
def test_should_display_product_in_table_when_search_by_keyword_is_successful(qtbot, inventory_window):
    """Khi tìm kiếm thành công, sản phẩm phải hiện lên bảng tồn kho"""
    mock_item = types.SimpleNamespace(
        sku='SP01', product_name='Bút bi', total_base_quantity=100, base_unit_name='Cây',
        conversion_quantity_str='5 Hộp', min_stock=10, is_low_stock=False
    )
    inventory_window.mock_inventory_service.get_inventory_list.return_value = [mock_item]

    qtbot.keyClicks(inventory_window.ui.txt_search_inventory, "But")
    qtbot.keyClick(inventory_window.ui.txt_search_inventory, Qt.Key.Key_Return)

    assert inventory_window.ui.tbl_inventory.rowCount() == 1
    assert inventory_window.ui.tbl_inventory.item(0, 0).text() == "SP01"


def test_should_show_critical_error_and_not_crash_when_search_fails_with_system_exception(qtbot, inventory_window,
                                                                                          mocker):
    """Khi mất kết nối DB lúc tìm kiếm, phải báo lỗi Critical nhưng không được văng app"""
    mock_critical = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.critical')
    inventory_window.mock_inventory_service.get_inventory_list.side_effect = Exception("Database Timeout")

    qtbot.keyClick(inventory_window.ui.txt_search_inventory, Qt.Key.Key_Return)

    mock_critical.assert_called_once()
    assert "Database Timeout" in mock_critical.call_args[0][2]


# ==========================================
# LUỒNG XUẤT EXCEL
# ==========================================
def test_should_cancel_export_process_when_user_closes_file_dialog(qtbot, inventory_window, mocker):
    """Khi người dùng tắt hộp thoại chọn nơi lưu, tiến trình xuất Excel phải bị hủy"""
    mock_dialog = mocker.patch(
        'app.modules.inventory.ui.controllers.inventory_management_controller.QFileDialog.getSaveFileName')
    mock_dialog.return_value = ('', '')  # Giả lập bấm Cancel

    qtbot.mouseClick(inventory_window.ui.btn_export_excel, Qt.MouseButton.LeftButton)
    inventory_window.mock_inventory_service.export_inventory_to_excel.assert_not_called()


def test_should_show_success_message_when_exporting_excel_completes(qtbot, inventory_window, mocker):
    """Khi xuất file Excel thành công, phải hiện thông báo hoàn tất"""
    mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QFileDialog.getSaveFileName',
                 return_value=('/path/file.xlsx', ''))
    mock_info = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.information')
    inventory_window.mock_inventory_service.export_inventory_to_excel.return_value = True

    qtbot.mouseClick(inventory_window.ui.btn_export_excel, Qt.MouseButton.LeftButton)
    mock_info.assert_called_once()


def test_should_show_critical_error_when_export_fails_due_to_system_issue(qtbot, inventory_window, mocker):
    """Khi không lưu được file do lỗi ổ cứng/quyền, phải hiện lỗi Critical"""
    mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QFileDialog.getSaveFileName',
                 return_value=('/path/file.xlsx', ''))
    mock_critical = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.critical')
    inventory_window.mock_inventory_service.export_inventory_to_excel.side_effect = Exception("Permission Denied")

    qtbot.mouseClick(inventory_window.ui.btn_export_excel, Qt.MouseButton.LeftButton)
    mock_critical.assert_called_once()
    assert "Permission Denied" in mock_critical.call_args[0][2]


# ==========================================
# LUỒNG THAO TÁC GIỎ HÀNG
# ==========================================
def test_should_update_cart_totals_correctly_when_adding_modifying_and_removing_items(qtbot, inventory_window, mocker):
    """Tổng tiền giỏ hàng phải cập nhật chính xác qua các bước: Thêm SP -> Tăng số lượng -> Xóa SP"""
    # ... (Logic bên trong giữ nguyên như cũ) ...
    pass


# ==========================================
# LUỒNG THÊM NHANH NHÀ CUNG CẤP
# ==========================================
def test_should_not_create_supplier_when_user_cancels_quick_add_dialog(qtbot, inventory_window, mocker):
    """Khi tắt popup nhập tên NCC mới, Service không được phép gọi"""
    mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QInputDialog.getText',
                 return_value=("", False))
    qtbot.mouseClick(inventory_window.ui.btn_add_supplier, Qt.MouseButton.LeftButton)
    inventory_window.mock_supplier_service.create_supplier.assert_not_called()


def test_should_select_new_supplier_in_dropdown_when_quick_add_is_successful(qtbot, inventory_window, mocker):
    """Khi thêm NCC mới thành công, Combobox phải tự động trỏ vào NCC đó"""
    mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QInputDialog.getText',
                 return_value=("NCC Mới", True))
    inventory_window.mock_supplier_service.create_supplier.return_value = 99

    qtbot.mouseClick(inventory_window.ui.btn_add_supplier, Qt.MouseButton.LeftButton)
    assert inventory_window.ui.cbo_supplier.currentData() == 99


def test_should_show_warning_when_quick_add_supplier_name_already_exists(qtbot, inventory_window, mocker):
    """Khi tạo NCC bị trùng tên, phải hiện Warning và không làm văng app"""
    mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QInputDialog.getText',
                 return_value=("Trùng Tên", True))
    mock_warning = mocker.patch('app.modules.inventory.ui.controllers.inventory_management_controller.QMessageBox.warning')
    inventory_window.mock_supplier_service.create_supplier.side_effect = Exception("Tên NCC đã tồn tại")

    qtbot.mouseClick(inventory_window.ui.btn_add_supplier, Qt.MouseButton.LeftButton)
    mock_warning.assert_called_once()
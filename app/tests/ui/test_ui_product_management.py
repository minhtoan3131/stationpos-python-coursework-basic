import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.core.exceptions.validation_exception import ValidationException
from app.ui.product.controllers.product_management_controller import ProductManagementController
from app.modules.product.dtos.product_list_dto import ProductListDTO


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_products():
    return [
        ProductListDTO(
            id=1, sku="SP001", name="Bút bi Thiên Long", category_name="Bút viết",
            unit_name="Cây", retail_price=5000, wholesale_price=4500,
            barcode="893123456", supplier_name="Thiên Long",
            conversion_unit_name="Hộp", conversion_ratio=12
        ),
        ProductListDTO(
            id=2, sku="SP002", name="Tập vở 200 trang", category_name="Tập vở",
            unit_name="Quyển", retail_price=10000, wholesale_price=None,
            barcode="893654321", supplier_name="Hồng Hà",
            conversion_unit_name=None, conversion_ratio=None
        )
    ]


@pytest.fixture
def manager_window(qtbot, mock_products):
    """
    Khởi tạo Controller với Dependency Injection hoàn toàn bằng MagicMock.
    Không cần dùng mocker.patch phức tạp nữa!
    """
    mock_product_service = MagicMock()
    mock_category_service = MagicMock()
    mock_supplier_service = MagicMock()
    mock_unit_service = MagicMock()

    mock_product_service.get_product_list.return_value = mock_products

    # Khởi tạo UI và Bơm các mock service vào
    window = ProductManagementController(
        product_service=mock_product_service,
        category_service=mock_category_service,
        supplier_service=mock_supplier_service,
        unit_service=mock_unit_service
    )
    qtbot.addWidget(window)

    # Lưu lại để các hàm test bên dưới có thể assert
    window.mock_service = mock_product_service
    return window


# ==========================================
# Các hàm Test giữ nguyên logic, chỉ sửa phần assert
# ==========================================

def test_init_loads_data_to_table(manager_window):
    manager_window.mock_service.get_product_list.assert_called_once()
    table = manager_window.ui.tbl_products
    assert table.rowCount() == 2
    assert table.item(0, 1).text() == "SP001"
    assert table.item(1, 1).text() == "SP002"


def test_search_button_clicks(qtbot, manager_window, mock_products):
    manager_window.mock_service.reset_mock()
    qtbot.keyClicks(manager_window.ui.txt_search_keyword, "SP001")
    manager_window.mock_service.search_products.return_value = [mock_products[0]]

    qtbot.mouseClick(manager_window.ui.btn_search_products, Qt.MouseButton.LeftButton)

    manager_window.mock_service.search_products.assert_called_once()
    assert manager_window.mock_service.search_products.call_args[0][0].keyword == "SP001"
    assert manager_window.ui.tbl_products.rowCount() == 1


def test_search_enter_key(qtbot, manager_window, mock_products):
    manager_window.mock_service.reset_mock()
    qtbot.keyClicks(manager_window.ui.txt_search_keyword, "Vo")
    manager_window.mock_service.search_products.return_value = [mock_products[1]]

    qtbot.keyClick(manager_window.ui.txt_search_keyword, Qt.Key.Key_Return)
    manager_window.mock_service.search_products.assert_called_once()


def test_open_create_dialog_success(qtbot, manager_window, mocker):
    manager_window.mock_service.reset_mock()
    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')
    mock_dialog_class.return_value.exec.return_value = 1

    qtbot.mouseClick(manager_window.ui.btn_create_product, Qt.MouseButton.LeftButton)

    # Kiểm tra xem Form con có được khởi tạo với ĐỦ 4 SERVICE không
    mock_dialog_class.assert_called_once_with(
        product_service=manager_window.product_service,
        category_service=manager_window.category_service,
        supplier_service=manager_window.supplier_service,
        unit_service=manager_window.unit_service
    )
    manager_window.mock_service.get_product_list.assert_called_once()


def test_open_update_dialog_without_selection(qtbot, manager_window, mocker):
    manager_window.ui.tbl_products.clearSelection()
    mock_msg_box = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')
    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')

    qtbot.mouseClick(manager_window.ui.btn_update_product, Qt.MouseButton.LeftButton)

    mock_msg_box.assert_called_once()
    mock_dialog_class.assert_not_called()


def test_open_update_dialog_success(qtbot, manager_window, mocker):
    manager_window.mock_service.reset_mock()
    manager_window.ui.tbl_products.setCurrentCell(0, 0)
    expected_id = int(manager_window.ui.tbl_products.item(0, 0).text())

    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')
    mock_dialog_class.return_value.exec.return_value = 1

    qtbot.mouseClick(manager_window.ui.btn_update_product, Qt.MouseButton.LeftButton)

    # Kiểm tra xem Form con có nhận đủ 4 Service + product_id hay không
    mock_dialog_class.assert_called_once_with(
        product_service=manager_window.product_service,
        category_service=manager_window.category_service,
        supplier_service=manager_window.supplier_service,
        unit_service=manager_window.unit_service,
        product_id=expected_id
    )
    manager_window.mock_service.get_product_list.assert_called_once()


def test_delete_product_without_selection(qtbot, manager_window, mocker):
    manager_window.ui.tbl_products.clearSelection()
    mock_info = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')
    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)
    manager_window.mock_service.delete_product.assert_not_called()


def test_delete_product_confirm_yes_success(qtbot, manager_window, mocker):
    manager_window.mock_service.reset_mock()
    manager_window.ui.tbl_products.setCurrentCell(0, 0)

    mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.question',
                 return_value=QMessageBox.StandardButton.Yes)
    mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')

    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)

    manager_window.mock_service.delete_product.assert_called_once()
    manager_window.mock_service.get_product_list.assert_called_once()


def test_delete_product_validation_error(qtbot, manager_window, mocker):
    manager_window.mock_service.reset_mock()
    manager_window.ui.tbl_products.setCurrentCell(0, 0)

    mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.question',
                 return_value=QMessageBox.StandardButton.Yes)
    mock_warning = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.warning')

    manager_window.mock_service.delete_product.side_effect = ValidationException("Sản phẩm vẫn còn tồn kho!")
    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
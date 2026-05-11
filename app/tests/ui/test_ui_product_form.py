import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt

from app.core.exceptions.validation_exception import ValidationException
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.ui.product.controllers.product_form_controller import ProductFormController
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO


# ==========================================
# FIXTURES
# ==========================================
@pytest.fixture
def mock_ref_data():
    return {
        "categories": [{'id': 1, 'name': 'Bút viết'}, {'id': 2, 'name': 'Tập vở'}],
        "suppliers": [{'id': 1, 'name': 'Thiên Long'}],
        "units": [{'id': 1, 'name': 'Cây'}, {'id': 2, 'name': 'Hộp'}]
    }


@pytest.fixture
def mock_product_detail():
    return ProductDetailDTO(
        id=1, sku="SP001", name="Bút bi Thiên Long", barcode="893123456", description="Bút bi mực xanh",
        category_id=1, category_name="Bút viết", supplier_id=1, supplier_name="Thiên Long",
        base_unit_id=1, base_unit_name="Cây", cost_price=4000, retail_price=5000, wholesale_price=4500,
        min_stock=10, conversion_unit_id=2, conversion_unit_name="Hộp", conversion_ratio=12, is_active=False,
    )


@pytest.fixture
def create_form(qtbot, mock_ref_data):
    """Tạo Form ở chế độ THÊM MỚI (product_id = None) dùng Dependency Injection hoàn toàn"""
    mock_prod_svc = MagicMock()
    mock_cat_svc = MagicMock()
    mock_sup_svc = MagicMock()
    mock_unit_svc = MagicMock()

    mock_cat_svc.get_all_categories.return_value = mock_ref_data["categories"]
    mock_sup_svc.get_all_suppliers.return_value = mock_ref_data["suppliers"]
    mock_unit_svc.get_all_units.return_value = mock_ref_data["units"]

    form = ProductFormController(
        product_service=mock_prod_svc,
        category_service=mock_cat_svc,
        supplier_service=mock_sup_svc,
        unit_service=mock_unit_svc,
        product_id=None
    )
    qtbot.addWidget(form)

    # Lưu lại để assert
    form.mock_prod_service = mock_prod_svc
    form.mock_category_service = mock_cat_svc
    form.mock_supplier_service = mock_sup_svc
    form.mock_unit_service = mock_unit_svc

    return form


# ==========================================
# KIỂM THỬ KHỞI TẠO & ĐỔ DỮ LIỆU
# ==========================================

def test_init_create_mode(create_form):
    form = create_form
    assert form.ui.lbl_main_title.text() == "THÊM MỚI SẢN PHẨM"
    assert form.ui.txt_sku.isEnabled() is True
    assert form.ui.cbo_category.count() == 2
    assert form.ui.cbo_supplier.count() == 2
    assert form.ui.cbo_conversion_unit.count() == 3


def test_init_update_mode_success(qtbot, mock_ref_data, mock_product_detail):
    mock_prod_svc = MagicMock()
    mock_cat_svc = MagicMock()
    mock_sup_svc = MagicMock()
    mock_unit_svc = MagicMock()

    mock_cat_svc.get_all_categories.return_value = mock_ref_data["categories"]
    mock_sup_svc.get_all_suppliers.return_value = mock_ref_data["suppliers"]
    mock_unit_svc.get_all_units.return_value = mock_ref_data["units"]
    mock_prod_svc.get_product_by_id.return_value = mock_product_detail

    form = ProductFormController(
        product_service=mock_prod_svc,
        category_service=mock_cat_svc,
        supplier_service=mock_sup_svc,
        unit_service=mock_unit_svc,
        product_id=1
    )
    qtbot.addWidget(form)

    assert form.ui.lbl_main_title.text() == "CẬP NHẬT SẢN PHẨM"
    assert form.ui.txt_sku.isEnabled() is False
    assert form.ui.txt_sku.text() == "SP001"
    assert form.ui.cbo_category.currentData() == 1
    mock_prod_svc.get_product_by_id.assert_called_once_with(1)


# ==========================================
# KIỂM THỬ TÍNH NĂNG "THÊM NHANH" (+)
# ==========================================

def test_quick_add_category_success(qtbot, create_form, mocker):
    form = create_form
    mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText',
                 return_value=("Văn phòng phẩm", True))
    form.mock_category_service.create_category.return_value = 99

    initial_count = form.ui.cbo_category.count()
    qtbot.mouseClick(form.ui.btn_add_category, Qt.MouseButton.LeftButton)

    form.mock_category_service.create_category.assert_called_once_with("Văn phòng phẩm")
    assert form.ui.cbo_category.count() == initial_count + 1
    assert form.ui.cbo_category.currentData() == 99


def test_quick_add_supplier_success(qtbot, create_form, mocker):
    form = create_form
    mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText',
                 return_value=("Bến Nghé", True))
    form.mock_supplier_service.create_supplier.return_value = 55

    qtbot.mouseClick(form.ui.btn_add_supplier, Qt.MouseButton.LeftButton)
    form.mock_supplier_service.create_supplier.assert_called_once_with("Bến Nghé")
    assert form.ui.cbo_supplier.currentData() == 55


def test_quick_add_unit_success_updates_both_comboboxes(qtbot, create_form, mocker):
    form = create_form
    mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText', return_value=("Lốc", True))
    form.mock_unit_service.create_unit.return_value = 88

    initial_base_count = form.ui.cbo_base_unit.count()
    initial_conv_count = form.ui.cbo_conversion_unit.count()

    qtbot.mouseClick(form.ui.btn_add_base_unit, Qt.MouseButton.LeftButton)

    form.mock_unit_service.create_unit.assert_called_once_with("Lốc")
    assert form.ui.cbo_base_unit.count() == initial_base_count + 1
    assert form.ui.cbo_conversion_unit.count() == initial_conv_count + 1
    assert form.ui.cbo_base_unit.currentData() == 88


def test_quick_add_cancel_or_empty(qtbot, create_form, mocker):
    form = create_form
    mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText',
                 return_value=("Một cái tên", False))
    qtbot.mouseClick(form.ui.btn_add_supplier, Qt.MouseButton.LeftButton)
    form.mock_supplier_service.create_supplier.assert_not_called()


# ==========================================
# KIỂM THỬ LƯU DỮ LIỆU (SAVE - HAPPY PATH)
# ==========================================

def test_save_new_product_success(qtbot, create_form, mocker):
    form = create_form

    form.ui.txt_sku.setText("SP-NEW-01")
    form.ui.txt_name.setText("Bút máy cao cấp")
    form.ui.txt_barcode.setText("1234567890123")
    form.ui.cbo_category.setCurrentIndex(0)
    form.ui.cbo_supplier.setCurrentIndex(1)
    form.ui.cbo_base_unit.setCurrentIndex(0)
    form.ui.spn_cost_price.setValue(50000)
    form.ui.spn_retail_price.setValue(80000)
    form.ui.spn_min_stock.setValue(15)

    form.mock_prod_service.create_product.return_value = 999
    mock_info = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.information')
    mock_accept = mocker.patch.object(form, 'accept')

    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    form.mock_prod_service.create_product.assert_called_once()
    dto = form.mock_prod_service.create_product.call_args[0][0]

    assert isinstance(dto, ProductCreateDTO)
    assert dto.sku == "SP-NEW-01"
    assert dto.cost_price == 50000
    assert dto.conversion_unit_id is None

    mock_info.assert_called_once()
    mock_accept.assert_called_once()


# ==========================================
# KIỂM THỬ ERROR HANDLING
# ==========================================

def test_save_product_validation_error(qtbot, create_form, mocker):
    form = create_form
    form.mock_prod_service.create_product.side_effect = ValidationException("Tên sản phẩm rỗng")
    mock_warning = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.warning')
    mock_accept = mocker.patch.object(form, 'accept')

    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    form.mock_prod_service.create_product.assert_called_once()
    mock_warning.assert_called_once()
    mock_accept.assert_not_called()


def test_save_product_system_error(qtbot, create_form, mocker):
    form = create_form
    form.mock_prod_service.create_product.side_effect = Exception("Mất kết nối DB")
    mock_critical = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.critical')
    mock_accept = mocker.patch.object(form, 'accept')

    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    mock_critical.assert_called_once()
    mock_accept.assert_not_called()
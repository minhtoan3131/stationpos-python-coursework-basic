import pytest
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
    """Giả lập 1 DTO Chi tiết Sản phẩm trả về từ Database để test chế độ Update"""
    return ProductDetailDTO(
        id=1,
        sku="SP001",
        name="Bút bi Thiên Long",
        barcode="893123456",
        description="Bút bi mực xanh",
        category_id=1, category_name="Bút viết",
        supplier_id=1, supplier_name="Thiên Long",
        base_unit_id=1, base_unit_name="Cây",
        cost_price=4000,
        retail_price=5000,
        wholesale_price=4500,
        min_stock=10,
        conversion_unit_id=2, conversion_unit_name="Hộp",
        conversion_ratio=12,
        is_active=False,
    )


@pytest.fixture
def create_form(qtbot, mocker, mock_ref_data):
    """Fixture tạo Form ở chế độ THÊM MỚI (product_id = None)"""
    mock_prod_class = mocker.patch('app.ui.product.controllers.product_form_controller.ProductServiceImpl')
    mock_ref_class = mocker.patch('app.ui.product.controllers.product_form_controller.ReferenceDataService')

    mock_ref_instance = mock_ref_class.return_value
    mock_ref_instance.get_all_categories.return_value = mock_ref_data["categories"]
    mock_ref_instance.get_all_suppliers.return_value = mock_ref_data["suppliers"]
    mock_ref_instance.get_all_units.return_value = mock_ref_data["units"]

    form = ProductFormController(product_id=None)
    qtbot.addWidget(form)
    form.mock_prod_service = mock_prod_class.return_value
    form.mock_ref_service = mock_ref_instance
    return form


# ==========================================
# KIỂM THỬ KHỞI TẠO & ĐỔ DỮ LIỆU
# ==========================================

def test_init_create_mode(create_form):
    """
    Kịch bản: Khởi tạo Form không truyền ID.
    Kỳ vọng: Chế độ THÊM MỚI. Tiêu đề đúng, SKU mở khóa, Combobox có đủ dữ liệu.
    """
    form = create_form

    # Kiểm tra Tiêu đề và Trạng thái ô nhập liệu
    assert form.ui.lbl_main_title.text() == "THÊM MỚI SẢN PHẨM"
    assert form.ui.txt_sku.isEnabled() is True  # SKU phải được phép nhập

    # Danh mục có 2 item
    assert form.ui.cbo_category.count() == 2

    # Nhà cung cấp có 2 item (1 item "--- Không chọn ---" sinh ra từ code + 1 item từ DB)
    assert form.ui.cbo_supplier.count() == 2
    assert form.ui.cbo_supplier.itemText(0) == "--- Không chọn ---"

    # ĐVT Quy đổi (Sỉ) có 3 item (1 item "--- Không có ---" + 2 item từ DB)
    assert form.ui.cbo_conversion_unit.count() == 3


def test_init_update_mode_success(qtbot, mocker, mock_ref_data, mock_product_detail):
    """
    Kịch bản: Khởi tạo Form truyền product_id = 1.
    Kỳ vọng: Chế độ CẬP NHẬT. Khóa ô SKU, tự động điền toàn bộ dữ liệu từ DTO lên UI.
    """
    # SETUP: Patch 2 Services
    mock_prod_class = mocker.patch('app.ui.product.controllers.product_form_controller.ProductServiceImpl')
    mock_ref_class = mocker.patch('app.ui.product.controllers.product_form_controller.ReferenceDataService')

    mock_prod_instance = mock_prod_class.return_value
    mock_ref_instance = mock_ref_class.return_value

    # Bơm dữ liệu từ điển
    mock_ref_instance.get_all_categories.return_value = mock_ref_data["categories"]
    mock_ref_instance.get_all_suppliers.return_value = mock_ref_data["suppliers"]
    mock_ref_instance.get_all_units.return_value = mock_ref_data["units"]

    # Bơm dữ liệu Chi tiết Sản phẩm khi Controller gọi get_product_by_id
    mock_prod_instance.get_product_by_id.return_value = mock_product_detail

    # KHỞI TẠO FORM VỚI ID = 1
    form = ProductFormController(product_id=1)
    qtbot.addWidget(form)

    # Kiểm tra Giao diện
    assert form.ui.lbl_main_title.text() == "CẬP NHẬT SẢN PHẨM"
    assert form.ui.txt_sku.isEnabled() is False  # Không cho sửa SKU

    assert form.ui.txt_sku.text() == "SP001"
    assert form.ui.txt_name.text() == "Bút bi Thiên Long"
    assert form.ui.txt_barcode.text() == "893123456"

    assert form.ui.spn_cost_price.value() == 4000
    assert form.ui.spn_retail_price.value() == 5000
    assert form.ui.spn_conversion_ratio.value() == 12

    # Dữ liệu Combobox (Kiểm tra xem nó có Select đúng item không)
    # currentData() sẽ lấy ra ID ẩn bên dưới, chứ không phải text hiển thị
    assert form.ui.cbo_category.currentData() == 1  # Category ID = 1
    assert form.ui.cbo_supplier.currentData() == 1  # Supplier ID = 1
    assert form.ui.cbo_conversion_unit.currentData() == 2  # Conversion Unit ID = 2 (Hộp)

    # Xác minh Service đã được gọi
    mock_prod_instance.get_product_by_id.assert_called_once_with(1)


# ==========================================
# KIỂM THỬ TÍNH NĂNG "THÊM NHANH" (+)
# ==========================================

def test_quick_add_category_success(qtbot, create_form, mocker):
    """
    Kịch bản: Bấm nút (+) ở Danh mục, nhập "Văn phòng phẩm" và OK.
    Kỳ vọng: Service tạo mới được gọi. Combobox thêm item mới và tự động chọn item đó.
    """
    form = create_form

    # Patch hộp thoại nhập text để tự động trả về chuỗi "Văn phòng phẩm" và trạng thái True (OK)
    mock_input = mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText')
    mock_input.return_value = ("Văn phòng phẩm", True)

    # Thiết lập Mock Service trả về ID = 99 khi tạo thành công
    form.mock_ref_service.create_category.return_value = 99

    # Lấy số lượng item trong combobox trước khi thêm (Đang có 2 item từ Fixture)
    initial_count = form.ui.cbo_category.count()

    # WHEN: Click nút (+) Thêm Danh mục
    qtbot.mouseClick(form.ui.btn_add_category, Qt.MouseButton.LeftButton)

    # THEN
    # Đảm bảo popup đã được gọi lên
    mock_input.assert_called_once()

    # Đảm bảo Service đã được gọi để lưu chữ "Văn phòng phẩm"
    form.mock_ref_service.create_category.assert_called_once_with("Văn phòng phẩm")

    # Đảm bảo Combobox đã tăng thêm 1 item
    assert form.ui.cbo_category.count() == initial_count + 1

    # Đảm bảo Combobox ĐANG CHỌN đúng cái item mới tạo đó (ID = 99)
    assert form.ui.cbo_category.currentData() == 99
    assert form.ui.cbo_category.currentText() == "Văn phòng phẩm"


def test_quick_add_unit_success_updates_both_comboboxes(qtbot, create_form, mocker):
    """
    Kịch bản: Bấm nút (+) ở ĐVT Cơ bản, nhập "Lốc" và OK.
    Kỳ vọng: Item mới phải được nạp vào CẢ 2 Combobox (ĐVT Lẻ và ĐVT Sỉ), và tự chọn ở ĐVT Lẻ.
    """
    form = create_form
    mock_input = mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText')
    mock_input.return_value = ("Lốc", True)

    form.mock_ref_service.create_unit.return_value = 88

    # Lấy số lượng trước khi thêm
    initial_base_count = form.ui.cbo_base_unit.count()
    initial_conv_count = form.ui.cbo_conversion_unit.count()

    # WHEN: Click nút (+) ở Đơn vị cơ bản
    qtbot.mouseClick(form.ui.btn_add_base_unit, Qt.MouseButton.LeftButton)

    # Service được gọi với đúng chữ "Lốc"
    form.mock_ref_service.create_unit.assert_called_once_with("Lốc")

    # Cả 2 Combobox Đều phải tăng thêm 1 item
    assert form.ui.cbo_base_unit.count() == initial_base_count + 1
    assert form.ui.cbo_conversion_unit.count() == initial_conv_count + 1

    # Tự động chọn "Lốc" ở Combobox ĐVT Cơ bản (Nơi người dùng vừa bấm nút)
    assert form.ui.cbo_base_unit.currentData() == 88


def test_quick_add_cancel_or_empty(qtbot, create_form, mocker):
    """
    Kịch bản: Bấm nút (+) nhưng người dùng để trống hoặc bấm Hủy (Cancel).
    Kỳ vọng: Hệ thống không làm gì cả, không gọi Service, không lỗi.
    """
    form = create_form
    mock_input = mocker.patch('app.ui.product.controllers.product_form_controller.QInputDialog.getText')

    # Giả lập người dùng bấm nút Cancel (trả về False)
    mock_input.return_value = ("Một cái tên", False)

    # WHEN: Click nút (+)
    qtbot.mouseClick(form.ui.btn_add_supplier, Qt.MouseButton.LeftButton)

    # THEN: Service tuyệt đối không được gọi
    form.mock_ref_service.create_supplier.assert_not_called()


# ==========================================
# KIỂM THỬ LƯU DỮ LIỆU (SAVE - HAPPY PATH)
# ==========================================

def test_save_new_product_success(qtbot, create_form, mocker):
    """
    Kịch bản: Điền đầy đủ thông tin hợp lệ và bấm Lưu (chế độ Tạo mới).
    Kỳ vọng: Gọi Service create_product với DTO chuẩn xác, hiện popup thành công và tự đóng form.
    """
    form = create_form

    # GIVEN 1
    # Bơm dữ liệu giả lập thao tác nhập của người dùng vào giao diện
    form.ui.txt_sku.setText("SP-NEW-01")
    form.ui.txt_name.setText("Bút máy cao cấp")
    form.ui.txt_barcode.setText("1234567890123")

    # Chọn Combobox
    # (Index 0 của cbo_supplier là "--- Không chọn ---", nên Index 1 chính là "Thiên Long" - ID: 1)
    form.ui.cbo_category.setCurrentIndex(0)  # Lấy item đầu tiên (Bút viết, ID: 1)
    form.ui.cbo_supplier.setCurrentIndex(1)  # Lấy Thiên Long (ID: 1)
    form.ui.cbo_base_unit.setCurrentIndex(0)  # Lấy Cây (ID: 1)

    # Nhập giá tiền và tồn kho
    form.ui.spn_cost_price.setValue(50000)
    form.ui.spn_retail_price.setValue(80000)
    form.ui.spn_min_stock.setValue(15)

    # GIVEN 2
    # Thiết lập Mock Service trả về ID hệ thống mới = 999
    form.mock_prod_service.create_product.return_value = 999

    mock_info = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.information')

    # Chặn lệnh đóng Form (self.accept()) để test không bị mất context
    mock_accept = mocker.patch.object(form, 'accept')

    # WHEN: Giả lập click chuột vào nút "Lưu thông tin"
    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    # THEN
    # Kiểm tra Service lưu dữ liệu được gọi đúng 1 lần
    form.mock_prod_service.create_product.assert_called_once()

    # Kiểm tra dto gửi gom lại gửi đi
    args, kwargs = form.mock_prod_service.create_product.call_args
    dto = args[0]

    assert isinstance(dto, ProductCreateDTO)
    assert dto.sku == "SP-NEW-01"
    assert dto.name == "Bút máy cao cấp"
    assert dto.barcode == "1234567890123"
    assert dto.category_id == 1
    assert dto.supplier_id == 1
    assert dto.base_unit_id == 1
    assert dto.cost_price == 50000
    assert dto.retail_price == 80000
    assert dto.min_stock == 15
    # Dkhông điền giá sỉ và quy đổi, nó phải tự động là None/0
    assert dto.conversion_unit_id is None

    # Đảm bảo Popup thành công đã bật lên, và trong câu thông báo có chứa ID "999"
    mock_info.assert_called_once()
    assert "999" in mock_info.call_args[0][2]

    # Đảm bảo form đã gọi lệnh đóng cửa sổ
    mock_accept.assert_called_once()


# ==========================================
# KIỂM THỬ ERROR HANDLING
# ==========================================

def test_save_product_validation_error(qtbot, create_form, mocker):
    """
    Kịch bản: Bấm Lưu nhưng dữ liệu không hợp lệ (Tầng Core ném lỗi ValidationException).
    Kỳ vọng: Form bắt được lỗi, hiện popup Cảnh báo, và không đóng form.
    """
    # GIVEN
    form = create_form
    # Giả lập tầng Service ném lỗi khi hàm create_product được gọi
    form.mock_prod_service.create_product.side_effect = ValidationException("Tên sản phẩm không được để trống.")

    # Patch hộp thoại Warning
    mock_warning = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.warning')

    # Patch lệnh đóng form (accept) để lát nữa kiểm tra
    mock_accept = mocker.patch.object(form, 'accept')

    # WHEN: Click nút "Lưu thông tin"
    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    # THEN
    # Service chắc chắn đã bị gọi và văng lỗi
    form.mock_prod_service.create_product.assert_called_once()

    # Controller phải hứng được lỗi và bung popup Warning
    mock_warning.assert_called_once()
    args, kwargs = mock_warning.call_args
    assert "Tên sản phẩm không được để trống" in args[2]  # args[2] chứa nội dung thông báo

    # Form không được phép đóng
    mock_accept.assert_not_called()


def test_save_product_system_error(qtbot, create_form, mocker):
    """
    Kịch bản: Lỗi hệ thống bất ngờ (mất kết nối DB, crash server...).
    Kỳ vọng: Hiện popup Lỗi nghiêm trọng (Critical) và không sập app.
    """
    form = create_form

    # GIVEN
    # Giả lập lỗi hệ thống bất ngờ (Exception thuần)
    form.mock_prod_service.create_product.side_effect = Exception("Mất kết nối Database")

    # Patch hộp thoại Critical
    mock_critical = mocker.patch('app.ui.product.controllers.product_form_controller.QMessageBox.critical')
    mock_accept = mocker.patch.object(form, 'accept')

    # WHEN: Click nút Lưu
    qtbot.mouseClick(form.ui.btn_save, Qt.MouseButton.LeftButton)

    # THEN:
    mock_critical.assert_called_once()
    args, kwargs = mock_critical.call_args
    assert "Mất kết nối Database" in args[2]  # Thông báo phải chứa chi tiết lỗi hệ thống

    mock_accept.assert_not_called()
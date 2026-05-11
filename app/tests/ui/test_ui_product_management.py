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
    """Tạo 2 sản phẩm giả lập để test bảng"""
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
def manager_window(qtbot, mocker, mock_products):
    """
    Khởi tạo Controller, chặn gọi DB thật và gài dữ liệu giả vào.
    """
    mock_service_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductServiceImpl')
    mock_service_instance = mock_service_class.return_value

    mock_service_instance.get_product_list.return_value = mock_products

    # Khởi tạo UI (Lúc này UI sẽ gọi mock_service_instance thay vì đồ thật)
    window = ProductManagementController()
    qtbot.addWidget(window)

    # Lưu lại mock instance vào window để các test case có thể dễ dàng assert
    window.mock_service = mock_service_instance

    return window


# ==========================================
# Kiểm thử khởi tạo & Bảng dữ liệu
# ==========================================

def test_init_loads_data_to_table(manager_window):
    """
    Kịch bản: Mở màn hình quản lý sản phẩm.
    Kỳ vọng: Gọi Service 1 lần, hiển thị đúng 2 dòng, format số tiền và gộp ĐVT sỉ chính xác.
    """
    # Kiểm tra Service có được gọi lúc __init__ không
    manager_window.mock_service.get_product_list.assert_called_once()

    table = manager_window.ui.tbl_products

    # Kiểm tra cấu trúc tổng thể của Bảng
    assert table.rowCount() == 2
    assert table.columnCount() == 9
    assert table.isColumnHidden(0) is True  # Cột ID (0) phải bị ẩn đi

    # Kiểm tra Dòng 0: Sản phẩm có đủ Quy đổi (SP001)
    assert table.item(0, 1).text() == "SP001"
    assert table.item(0, 2).text() == "Bút bi Thiên Long"
    assert table.item(0, 4).text() == "Cây"  # ĐVT Cơ bản
    assert table.item(0, 5).text() == "5,000"  # Giá lẻ đã có dấu phẩy
    assert table.item(0, 6).text() == "Hộp (12 Cây)"
    assert table.item(0, 7).text() == "4,500"  # Giá sỉ

    # Kiểm tra Dòng 1: Sản phẩm KHÔNG CÓ Quy đổi sỉ (SP002)
    assert table.item(1, 1).text() == "SP002"
    assert table.item(1, 5).text() == "10,000"
    assert table.item(1, 6).text() == "---"
    assert table.item(1, 7).text() == "---"


# ==========================================
# Kiểm thử tìm kiếm
# ==========================================

def test_search_button_clicks(qtbot, manager_window, mock_products):
    """
    Kịch bản: Nhập từ khóa 'SP001' và click nút Tìm kiếm.
    Kỳ vọng: Service search_products được gọi với đúng keyword='SP001'.
    Gọi Service đúng tham số và bảng dữ liệu phải lọc lại chỉ còn 1 dòng.
    """
    # Xóa lịch sử gọi hàm của Mock (nếu có) để test case được sạch
    manager_window.mock_service.reset_mock()

    # GIVEN: Gõ chữ 'SP001' vào ô tìm kiếm (Giả lập thao tác gõ phím)
    qtbot.keyClicks(manager_window.ui.txt_search_keyword, "SP001")
    manager_window.mock_service.search_products.return_value = [mock_products[0]]

    # WHEN: Giả lập click chuột trái vào nút Tìm kiếm
    qtbot.mouseClick(manager_window.ui.btn_search_products, Qt.MouseButton.LeftButton)

    # THEN:
    manager_window.mock_service.search_products.assert_called_once()

    # Bóc tách tham số (DTO) được truyền vào hàm search_products để kiểm tra
    args, kwargs = manager_window.mock_service.search_products.call_args
    filter_dto = args[0]  # Tham số đầu tiên chính là ProductFilterDTO

    assert filter_dto.keyword == "SP001"
    assert filter_dto.is_active is True

    table = manager_window.ui.tbl_products
    assert table.rowCount() == 1  # Bảng ban đầu có 2 dòng, giờ tìm kiếm xong chỉ còn 1 dòng
    assert table.item(0, 1).text() == "SP001"


def test_search_enter_key(qtbot, manager_window, mock_products):
    """
    Kịch bản: Nhập từ khóa 'Vở' và bấm phím Enter ngay trên textbox.
    Kỳ vọng: Hàm tìm kiếm vẫn phải được kích hoạt bình thường.
    """
    manager_window.mock_service.reset_mock()

    # GIVEN: Gõ từ khóa vào ô textbox
    qtbot.keyClicks(manager_window.ui.txt_search_keyword, "Vo") # Không dùng tiếng việt vì qtbot chỉ hỗ trợ mã ASCII
    manager_window.mock_service.search_products.return_value = [mock_products[1]]

    # WHEN: Giả lập bấm phím Enter (Return) trên ô textbox đó
    qtbot.keyClick(manager_window.ui.txt_search_keyword, Qt.Key.Key_Return)

    # THEN: Service search_products cũng phải nhận được tín hiệu tìm kiếm
    manager_window.mock_service.search_products.assert_called_once()

    args, kwargs = manager_window.mock_service.search_products.call_args
    filter_dto = args[0]

    assert filter_dto.keyword == "Vo"


# ==========================================
# Kiểm thử mở form
# ==========================================

def test_open_create_dialog_success(qtbot, manager_window, mocker):
    """
    Kịch bản: Click nút "Thêm hàng mới". Người dùng lưu thành công trên Form con.
    Kỳ vọng: Form con bật lên không làm treo test, và Bảng dữ liệu tự động làm mới.
    """
    manager_window.mock_service.reset_mock()

    # GIVEN
    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')
    mock_dialog_instance = mock_dialog_class.return_value

    # Giả lập việc hàm exec() chạy và người dùng bấm Save thành công (trả về 1/True)
    mock_dialog_instance.exec.return_value = 1

    # WHEN: Click nút "+ Thêm hàng mới"
    qtbot.mouseClick(manager_window.ui.btn_create_product, Qt.MouseButton.LeftButton)

    # THEN
    # Đảm bảo Form con đã được khởi tạo (không có tham số) và gọi hàm exec()
    mock_dialog_class.assert_called_once_with()
    mock_dialog_instance.exec.assert_called_once()

    # Vì exec trả về 1 (True), ứng dụng phải gọi hàm tải lại danh sách
    manager_window.mock_service.get_product_list.assert_called_once()


def test_open_update_dialog_without_selection(qtbot, manager_window, mocker):
    """
    Kịch bản: Click nút "Chỉnh sửa" nhưng KHÔNG chọn dòng nào trên bảng.
    Kỳ vọng: Hiện popup hướng dẫn, KHÔNG mở Form con.
    """
    manager_window.ui.tbl_products.clearSelection()
    mock_msg_box = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')
    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')

    # WHEN: Click nút "Chỉnh sửa"
    qtbot.mouseClick(manager_window.ui.btn_update_product, Qt.MouseButton.LeftButton)

    # THEN
    # Hộp thoại hướng dẫn phải được bật lên
    mock_msg_box.assert_called_once()
    args, kwargs = mock_msg_box.call_args
    # args[2] là nội dung của thông báo
    assert "Vui lòng click chọn một sản phẩm" in args[2]

    # Đảm bảo an toàn Form Con KHÔNG được mở ra
    mock_dialog_class.assert_not_called()


def test_open_update_dialog_success(qtbot, manager_window, mocker):
    """
    Kịch bản: CHỌN dòng đầu tiên, click nút "Chỉnh sửa".
    Kỳ vọng: Form con bật lên kèm theo đúng ID sản phẩm đó.
    """
    manager_window.mock_service.reset_mock()

    # Chọn dòng 0 trong bảng
    manager_window.ui.tbl_products.setCurrentCell(0, 0)
    # Lấy ID thực tế đang nằm ẩn ở dòng 0 (để lát so sánh)
    expected_id = int(manager_window.ui.tbl_products.item(0, 0).text())

    mock_dialog_class = mocker.patch('app.ui.product.controllers.product_management_controller.ProductFormController')
    mock_dialog_instance = mock_dialog_class.return_value
    mock_dialog_instance.exec.return_value = 1  # Giả lập sửa xong

    # WHEN: Click nút "Chỉnh sửa"
    qtbot.mouseClick(manager_window.ui.btn_update_product, Qt.MouseButton.LeftButton)

    # THEN
    # Form Con phải được khởi tạo và có truyền id vào
    mock_dialog_class.assert_called_once_with(product_id=expected_id)
    mock_dialog_instance.exec.assert_called_once()

    # THEN Bảng dữ liệu tự làm mới sau khi sửa
    manager_window.mock_service.get_product_list.assert_called_once()


# ==========================================
# Kiểm thử nhóm xóa sản phẩm
# ==========================================

def test_delete_product_without_selection(qtbot, manager_window, mocker):
    """
    Kịch bản: Click nút Xóa nhưng KHÔNG chọn dòng nào.
    Kỳ vọng: Hiện popup hướng dẫn, KHÔNG gọi hàm xóa của Service.
    """
    manager_window.ui.tbl_products.clearSelection()

    # Patch hộp thoại Information
    mock_info = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')

    # WHEN: Bấm nút "Xóa bỏ"
    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)

    # THEN:
    mock_info.assert_called_once()
    args, kwargs = mock_info.call_args
    assert "Vui lòng click chọn một sản phẩm" in args[2]  # args[2] là nội dung text

    # Đảm bảo Service tuyệt đối KHÔNG được gọi
    manager_window.mock_service.delete_product.assert_not_called()


def test_delete_product_confirm_yes_success(qtbot, manager_window, mocker):
    """
    Kịch bản: CHỌN dòng 0, click Xóa. Popup xác nhận hiện lên, giả lập bấm "Yes". Service chạy thành công.
    Kỳ vọng: Gọi hàm xóa đúng ID, hiện popup thành công, bảng dữ liệu được refresh.
    """
    manager_window.mock_service.reset_mock()

    # Chọn dòng đầu tiên (chứa SP001, ID=1)
    manager_window.ui.tbl_products.setCurrentCell(0, 0)

    # Patch hộp thoại Question và ép nó trả về nút YES
    mock_question = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.question')
    mock_question.return_value = QMessageBox.StandardButton.Yes

    # Patch hộp thoại Information (báo thành công)
    mock_info = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.information')

    # WHEN: Bấm nút Xóa
    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)

    # THEN
    # Đảm bảo popup xác nhận đã bật lên
    mock_question.assert_called_once()

    # Đảm bảo hàm xóa của Service đã được gọi và bóc tách DTO kiểm tra ID
    manager_window.mock_service.delete_product.assert_called_once()
    dto = manager_window.mock_service.delete_product.call_args[0][0]
    assert dto.product_id == 1

    # Đảm bảo popup báo thành công đã bật lên
    mock_info.assert_called_once()
    assert "Đã xóa thành công" in mock_info.call_args[0][2]

    # Bảng dữ liệu tự động refresh
    manager_window.mock_service.get_product_list.assert_called_once()


def test_delete_product_validation_error(qtbot, manager_window, mocker):
    """
    Kịch bản: Chọn dòng 0, bấm Xóa. Đồng ý Yes. Nhưng kho vẫn còn hàng -> Service văng lỗi Validation.
    Kỳ vọng: Controller bắt được lỗi, bung popup Warning, ứng dụng không sập.
    """
    manager_window.mock_service.reset_mock()
    manager_window.ui.tbl_products.setCurrentCell(0, 0)

    # GIVEN
    # Giả lập người dùng bấm YES trên popup xác nhận
    mock_question = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.question')
    mock_question.return_value = QMessageBox.StandardButton.Yes

    # Patch hộp thoại Warning (Dùng để hứng lỗi)
    mock_warning = mocker.patch('app.ui.product.controllers.product_management_controller.QMessageBox.warning')

    # Thiết lập Service ném lỗi (side_effect) giống hệt logic của Validator ngoài đời thực
    manager_window.mock_service.delete_product.side_effect = ValidationException("Sản phẩm vẫn còn tồn kho!")

    # WHEN: Bấm nút Xóa
    qtbot.mouseClick(manager_window.ui.btn_delete_product, Qt.MouseButton.LeftButton)

    # THEN:
    # Service chắc chắn đã bị gọi
    manager_window.mock_service.delete_product.assert_called_once()

    # Hàm bắt lỗi (except ValidationException) đã hoạt động và gọi popup Cảnh báo!
    mock_warning.assert_called_once()
    assert "Sản phẩm vẫn còn tồn kho!" in mock_warning.call_args[0][2]
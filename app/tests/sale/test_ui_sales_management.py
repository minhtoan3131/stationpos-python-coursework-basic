import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from app.ui.sale.controllers.sales_management_controller import SalesManagementController


# ==========================================
# IXTURE KHỞI TẠO & HÀM PHỤ TRỢ
# ==========================================
@pytest.fixture
def sales_window(qtbot, mocker):
    mock_inventory_service = mocker.Mock()
    mock_product_service = mocker.Mock()
    mock_sale_service = mocker.Mock()

    # Mồi sẵn dữ liệu: 1 sản phẩm còn tồn kho, 1 sản phẩm hết tồn kho
    mock_product_service.get_product_sale_list.return_value = [
        {
            'id': 100, 'sku': 'SP01', 'name': 'Bút bi',
            'base_unit_id': 10, 'base_unit_name': 'Cái', 'retail_price': 5000,
            'stock_qty': 25,
            'conversion_unit_id': 11, 'conversion_unit_name': 'Hộp',
            'wholesale_price': 45000, 'ratio': 10
        },
        {
            'id': 101, 'sku': 'SP02', 'name': 'Sổ tay',
            'base_unit_id': 12, 'base_unit_name': 'Quyển', 'retail_price': 15000,
            'stock_qty': 0,  # HẾT HÀNG -> Sẽ bị UI ẩn đi
            'conversion_unit_id': 12, 'conversion_unit_name': 'Quyển',
            'wholesale_price': None, 'ratio': None
        }
    ]

    window = SalesManagementController(
        inventory_service=mock_inventory_service,
        product_service=mock_product_service,
        sale_service=mock_sale_service
    )
    qtbot.addWidget(window)

    window.mock_product_service = mock_product_service
    window.mock_sale_service = mock_sale_service
    return window


def seed_cart_data(window, qtbot):
    """Hàm phụ trợ: Giả lập thao tác thu ngân click đưa sản phẩm vào giỏ hàng"""
    window.ui.tbl_products_sales.setCurrentCell(0, 0)
    qtbot.mouseClick(window.ui.btn_add_to_cart, Qt.MouseButton.LeftButton)


# ==========================================
# LUỒNG HIỂN THỊ & TÌM KIẾM
# ==========================================
def test_should_display_products_with_valid_stock_when_window_initializes(sales_window):
    """Khi khởi tạo, chỉ hiện SP có tồn > 0. SP có đơn vị quy đổi phải hiện đủ 2 dòng (Lẻ + Sỉ)"""
    table = sales_window.ui.tbl_products_sales

    # Bút bi tồn 25, ratio 10 -> Lên 2 dòng (1 Lẻ, 1 Sỉ). Sổ tay tồn 0 -> Ẩn.
    assert table.rowCount() == 2

    # Dòng 0: ĐVT Cơ bản
    assert table.item(0, 0).text() == "SP01"
    assert table.item(0, 2).text() == "Cái"

    # Dòng 1: ĐVT Quy đổi (Màu xanh)
    assert table.item(1, 0).text() == "SP01"
    assert table.item(1, 2).text() == "Hộp"


def test_should_trigger_product_search_when_search_button_is_clicked(qtbot, sales_window):
    """Gõ từ khóa và bấm tìm kiếm phải kích hoạt lời gọi xuống Backend"""
    sales_window.mock_product_service.reset_mock()

    # Dùng setText thay vì qtbot.keyClicks để tránh lỗi Crash C++ khi gõ ký tự Unicode Tiếng Việt
    sales_window.ui.txt_search_sales.setText("Bút")
    qtbot.mouseClick(sales_window.ui.btn_search, Qt.MouseButton.LeftButton)

    sales_window.mock_product_service.get_product_sale_list.assert_called_once_with("Bút")


# ==========================================
# LUỒNG THAO TÁC GIỎ HÀNG
# ==========================================
def test_should_add_product_to_cart_and_calculate_total_when_add_button_is_clicked(qtbot, sales_window):
    """Chọn SP và bấm Thêm -> Giỏ hàng phải nhảy số và tính đúng tổng tiền"""
    seed_cart_data(sales_window, qtbot)

    cart_table = sales_window.ui.tbl_cart
    assert cart_table.rowCount() == 1
    assert cart_table.item(0, 0).text() == "SP01"

    # 1 cái giá 5,000đ
    assert sales_window.ui.lbl_total_bill.text() == "5,000 VND"


def test_should_increment_quantity_when_adding_an_already_existing_product_in_cart(qtbot, sales_window):
    """Bấm thêm SP đã có trong giỏ -> Tăng số lượng thay vì thêm dòng mới"""
    sales_window.ui.tbl_products_sales.setCurrentCell(0, 0)

    # Bấm 3 lần
    qtbot.mouseClick(sales_window.ui.btn_add_to_cart, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(sales_window.ui.btn_add_to_cart, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(sales_window.ui.btn_add_to_cart, Qt.MouseButton.LeftButton)

    cart_table = sales_window.ui.tbl_cart
    assert cart_table.rowCount() == 1

    spin_qty = cart_table.cellWidget(0, 3)
    assert spin_qty.value() == 3
    assert sales_window.ui.lbl_total_bill.text() == "15,000 VND"


def test_should_clear_all_items_when_user_confirms_cancel_bill(qtbot, sales_window, mocker):
    """Bấm Hủy Hóa Đơn và chọn Yes -> Xóa trắng giỏ hàng"""
    seed_cart_data(sales_window, qtbot)

    mocker.patch('app.ui.sale.controllers.sales_management_controller.QMessageBox.question',
                 return_value=QMessageBox.StandardButton.Yes)

    qtbot.mouseClick(sales_window.ui.btn_cancel_bill, Qt.MouseButton.LeftButton)

    assert sales_window.ui.tbl_cart.rowCount() == 0
    assert sales_window.ui.lbl_total_bill.text() == "0 VND"


# ==========================================
# CÁC KỊCH BẢN TỪ CHỐI (PRE-CONDITIONS)
# ==========================================
def test_should_show_warning_and_prevent_checkout_when_cart_is_empty(qtbot, sales_window, mocker):
    """Giỏ hàng trống thì cấm mở Hộp thoại thanh toán"""
    mock_warning = mocker.patch('app.ui.sale.controllers.sales_management_controller.QMessageBox.warning')

    qtbot.mouseClick(sales_window.ui.btn_checkout, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    sales_window.mock_sale_service.process_checkout.assert_not_called()


# ==========================================
# KỊCH BẢN THANH TOÁN (POST-CONDITIONS / HAPPY PATH)
# ==========================================
def test_should_process_checkout_and_reset_ui_when_checkout_dialog_is_confirmed(qtbot, sales_window, mocker):
    """Khi chốt thanh toán ở Popup thành công: Phải gọi Service, báo mã HĐ và làm sạch UI"""
    seed_cart_data(sales_window, qtbot)

    # Giả lập Popup thanh toán ấn Xác nhận
    mock_dialog_class = mocker.patch('app.ui.sale.controllers.sales_management_controller.CheckoutDialogController')
    mock_dialog_instance = mock_dialog_class.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.is_confirmed = True

    sales_window.mock_sale_service.process_checkout.return_value = "HD-TEST-123"
    mock_info = mocker.patch('app.ui.sale.controllers.sales_management_controller.QMessageBox.information')

    # Bấm nút THANH TOÁN
    qtbot.mouseClick(sales_window.ui.btn_checkout, Qt.MouseButton.LeftButton)

    # Verify kết quả
    mock_dialog_class.assert_called_once()
    sales_window.mock_sale_service.process_checkout.assert_called_once()
    mock_info.assert_called_once()
    assert "HD-TEST-123" in mock_info.call_args[0][2]

    # Giỏ hàng phải trống lại
    assert sales_window.ui.tbl_cart.rowCount() == 0


# ==========================================
# CÁC KỊCH BẢN LỖI (INVARIANTS / EXCEPTIONS)
# ==========================================
def test_should_abort_checkout_when_user_cancels_at_dialog(qtbot, sales_window, mocker):
    """Khi Popup thanh toán hiện lên nhưng thu ngân ấn Hủy/Esc -> Dừng tiến trình"""
    seed_cart_data(sales_window, qtbot)

    mock_dialog_class = mocker.patch('app.ui.sale.controllers.sales_management_controller.CheckoutDialogController')
    mock_dialog_instance = mock_dialog_class.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Rejected

    qtbot.mouseClick(sales_window.ui.btn_checkout, Qt.MouseButton.LeftButton)

    sales_window.mock_sale_service.process_checkout.assert_not_called()


def test_should_show_error_and_preserve_cart_when_checkout_fails_at_backend(qtbot, sales_window, mocker):
    """Nếu lúc ghi xuống DB/Kho bị lỗi: Phải báo lỗi ra màn hình và GIỮ NGUYÊN giỏ hàng"""
    seed_cart_data(sales_window, qtbot)

    # Dialog cho qua
    mock_dialog_class = mocker.patch('app.ui.sale.controllers.sales_management_controller.CheckoutDialogController')
    mock_dialog_instance = mock_dialog_class.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.is_confirmed = True

    # Service bị đứt mạng / Lỗi Validation
    sales_window.mock_sale_service.process_checkout.side_effect = Exception("Không đủ tồn kho!")
    mock_critical = mocker.patch('app.ui.sale.controllers.sales_management_controller.QMessageBox.critical')

    qtbot.mouseClick(sales_window.ui.btn_checkout, Qt.MouseButton.LeftButton)

    mock_critical.assert_called_once()
    assert "Không đủ tồn kho" in mock_critical.call_args[0][2]

    # Tuyệt đối không được xóa giỏ hàng của thu ngân
    assert sales_window.ui.tbl_cart.rowCount() == 1
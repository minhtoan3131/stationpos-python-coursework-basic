import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QSpinBox, QTableWidgetItem, QComboBox

from app.modules.inventory.ui.controllers.inventory_management_controller import InventoryManagementController


@pytest.fixture
def inventory_window(qtbot, mocker):
    """Fixture khởi tạo màn hình nhập kho và mock hoàn toàn các phân lớp Service"""
    mock_inv_service = MagicMock()
    mock_sup_service = MagicMock()
    mock_po_service = MagicMock()

    # Cấu hình giá trị trả về mặc định để form khởi tạo không lỗi
    mock_sup_service.get_all_suppliers.return_value = []
    mock_inv_service.get_inventory_list.return_value = []

    window = InventoryManagementController(
        inventory_service=mock_inv_service,
        supplier_service=mock_sup_service,
        po_history_service=mock_po_service
    )
    qtbot.addWidget(window)
    return window


def test_quantity_spinbox_should_have_maximum_limit(inventory_window, mocker):
    """
    CHỐT CHẶN 1: Trần số lượng SpinBox khi thêm hàng vào phiếu nhập.
    Kỳ vọng: QSpinBox được sinh ra trên dòng phải khóa cứng giá trị tối đa là 100,000 cái.
    """
    # GIVEN: Giả lập có 1 sản phẩm đang được chọn trong danh sách tồn kho bên trái
    fake_inventory_item = MagicMock()
    fake_inventory_item.sku = "SP001"
    fake_inventory_item.product_name = "Bút bi Thiên Long"
    fake_inventory_item.total_base_quantity = 50
    fake_inventory_item.base_unit_name = "Cây"
    fake_inventory_item.conversion_quantity_str = ""
    fake_inventory_item.min_stock = 10
    fake_inventory_item.is_low_stock = False

    inventory_window.raw_inventory_data[0] = fake_inventory_item

    # Mock ép cứngcurrentRow() trả về 0 để vượt qua chốt chặn hàng rỗng vật lý của Qt
    mocker.patch.object(inventory_window.ui.tbl_inventory, 'currentRow', return_value=0)

    # Mock thông tin sản phẩm phục vụ nạp vào giỏ hàng
    fake_product_detail = MagicMock()
    fake_product_detail.id = 1
    fake_product_detail.sku = "SP001"
    fake_product_detail.name = "Bút bi Thiên Long"
    fake_product_detail.base_unit_name = "Cây"
    fake_product_detail.base_unit_id = 1
    fake_product_detail.conversion_unit_id = None

    inventory_window.inventory_service.search_products_for_import.return_value = [fake_product_detail]

    # ACT: Kích hoạt thêm sản phẩm vào giỏ hàng bên phải
    inventory_window.add_selected_to_cart()

    # THEN: Xác minh ô nhập số lượng (Cột số 3) tồn tại và bị khống chế tối đa 100,000 cái
    spn_qty = inventory_window.ui.tbl_items.cellWidget(0, 3)
    assert spn_qty is not None, "Lỗi: Giỏ hàng trống rỗng, không tìm thấy ô SpinBox số lượng!"
    assert isinstance(spn_qty, QSpinBox)
    assert spn_qty.maximum() == 100000


def test_save_purchase_should_reject_when_single_price_exceeds_1_billion(inventory_window, mocker):
    """
    CHỐT CHẶN 2A: Đánh chặn Đơn giá nhập của từng mặt hàng gõ tay vượt quá 1 Tỷ VND.
    Kỳ vọng: Hiện QMessageBox cảnh báo và chặn đứng không cho gửi xuống Database.
    """
    # GIVEN: Thiết lập NCC hợp lệ và gài 1 dòng hàng có giá 2 Tỷ đồng (Vượt trần 1 Tỷ)
    inventory_window.ui.cbo_supplier.addItem("Nhà sách Hồng Hà", 1)
    inventory_window.ui.cbo_supplier.setCurrentIndex(1)
    inventory_window.ui.tbl_items.setRowCount(1)

    sku_item = QTableWidgetItem("SP001")
    sku_item.setData(Qt.ItemDataRole.UserRole, 1)
    inventory_window.ui.tbl_items.setItem(0, 0, sku_item)
    inventory_window.ui.tbl_items.setItem(0, 1, QTableWidgetItem("Bút bi"))

    cbo_unit = QComboBox()
    cbo_unit.addItem("Cây", 1)
    inventory_window.ui.tbl_items.setCellWidget(0, 2, cbo_unit)

    spn_qty = QSpinBox()
    spn_qty.setValue(1)
    inventory_window.ui.tbl_items.setCellWidget(0, 3, spn_qty)

    # Đút đơn giá gõ tay vượt trần an toàn
    inventory_window.ui.tbl_items.setItem(0, 4, QTableWidgetItem("2,000,000,000"))

    # Mock hộp thoại thông báo warning vòng ngoài của Qt
    mock_warning = mocker.patch('PyQt6.QtWidgets.QMessageBox.warning')

    # ACT: Bấm lưu phiếu nhập kho
    inventory_window.handle_save_purchase()

    # THEN: Hệ thống phải bẫy được lỗi, đưa thông báo và từ chối gọi Service ghi CSDL
    mock_warning.assert_called_once()
    assert "vượt quá hạn mức tối đa cho phép (1 Tỷ VND)" in mock_warning.call_args[0][2]
    inventory_window.inventory_service.create_purchase_order.assert_not_called()


def test_save_purchase_should_reject_when_total_po_exceeds_50_billion(inventory_window, mocker):
    """
    CHỐT CHẶN 2B: Đánh chặn Tổng tiền toàn bộ Phiếu nhập kho vượt quá 50 Tỷ VND.
    Kỳ vọng: Hiện QMessageBox.critical báo động đỏ và từ chối giao dịch hoàn toàn.
    """
    # GIVEN: Cấu hình phiếu nhập có số lượng 60,000 cái với giá 1,000,000đ -> Tổng đơn = 60 Tỷ VND (Vượt trần 50 Tỷ)
    inventory_window.ui.cbo_supplier.addItem("Nhà sách Fahasa", 2)
    inventory_window.ui.cbo_supplier.setCurrentIndex(1)
    inventory_window.ui.tbl_items.setRowCount(1)

    sku_item = QTableWidgetItem("SP002")
    sku_item.setData(Qt.ItemDataRole.UserRole, 2)
    inventory_window.ui.tbl_items.setItem(0, 0, sku_item)
    inventory_window.ui.tbl_items.setItem(0, 1, QTableWidgetItem("Sách ngoại văn lớn"))

    cbo_unit = QComboBox()
    cbo_unit.addItem("Cuốn", 2)
    inventory_window.ui.tbl_items.setCellWidget(0, 2, cbo_unit)

    spn_qty = QSpinBox()
    spn_qty.setMaximum(100000)
    spn_qty.setValue(60000)
    inventory_window.ui.tbl_items.setCellWidget(0, 3, spn_qty)

    inventory_window.ui.tbl_items.setItem(0, 4, QTableWidgetItem("1,000,000"))

    mock_critical = mocker.patch('PyQt6.QtWidgets.QMessageBox.critical')

    # ACT: Tiến hành hạ lệnh lưu phiếu nhập kho vĩ mô
    inventory_window.handle_save_purchase()

    # THEN: Hệ thống kích hoạt chuông cảnh báo tràn số tài chính vĩ mô, khóa cứng luồng ghi
    mock_critical.assert_called_once()
    assert "VƯỢT NGƯỠNG HẠN MỨC HỆ THỐNG" in mock_critical.call_args[0][2]
    inventory_window.inventory_service.create_purchase_order.assert_not_called()
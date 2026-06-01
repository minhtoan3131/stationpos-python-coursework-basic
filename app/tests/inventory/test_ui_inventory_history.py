import pytest
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QTableWidgetItem
from PyQt6.QtCore import Qt

from app.core.exceptions.validation_exception import ValidationException
from app.modules.inventory.dtos.po_history_dto import PurchaseOrderMasterDTO, PurchaseOrderDetailDTO
from app.modules.inventory.ui.controllers.inventory_history_controller import InventoryHistoryController
from app.modules.inventory.ui.generated.ui_inventory_management import Ui_InventoryManagementWidget


# ==========================================
# 1. SETUP FIXTURE CHO UI TEST
# ==========================================
@pytest.fixture
def mock_po_service(mocker):
    """Làm giả hoàn toàn tầng Service để cách ly UI khỏi Database"""
    return mocker.Mock()


@pytest.fixture
def history_ui(qtbot, mock_po_service):
    widget = QWidget()
    ui = Ui_InventoryManagementWidget()
    ui.setupUi(widget)
    widget.show()
    qtbot.addWidget(widget)
    ui.tabWidget_inventory.setCurrentIndex(1)
    controller = InventoryHistoryController(ui, mock_po_service)
    return controller, ui, mock_po_service, widget

    # Trả về cả widget để đảm bảo nó không bị hủy khi fixture thoát
    return controller, ui, mock_po_service, widget


# ==========================================
# 2. TEST UC1: LỌC VÀ XEM DANH SÁCH (MASTER)
# ==========================================
def test_uc1_load_master_data_updates_table_and_formats_colors(history_ui):
    """Kiểm tra: Dữ liệu tải lên bảng Master phải đúng màu sắc và reset bảng Detail (TC_Post_01, 02, 03)"""
    controller, ui, mock_service, _ = history_ui

    # 1. GIVEN: Service trả về 2 phiếu (1 Hợp lệ, 1 Đã hủy)
    mock_service.search_history.return_value = [
        PurchaseOrderMasterDTO(
            id=1, code="PN-001", created_at=datetime.now(), supplier_name="NCC A",
            total_amount=50000, status="COMPLETED", note="Hàng OK", cancel_reason=None
        ),
        PurchaseOrderMasterDTO(
            id=2, code="PN-002", created_at=datetime.now(), supplier_name="NCC B",
            total_amount=150000, status="CANCELLED", note="Hàng lỗi", cancel_reason="Sai số lượng"
        )
    ]

    # Trước khi load, ta giả lập bảng Detail đang có dữ liệu rác (để lát check xem nó có bị clear không)
    ui.tbl_po_details.setRowCount(5)

    # 2. WHEN: Gọi hàm load dữ liệu (Tương đương bấm nút Tìm kiếm)
    controller.load_master_data()

    # 3. THEN: Kiểm chứng các Post-conditions
    # TC_Post_01: Bảng Master phải có đúng 2 dòng
    assert ui.tbl_po_master.rowCount() == 2
    assert ui.tbl_po_master.item(0, 0).text() == "PN-001"
    assert ui.tbl_po_master.item(1, 0).text() == "PN-002"

    # TC_Post_02: Định dạng màu sắc chữ ở cột Trạng thái (Cột số 4)
    # Dòng 0 (COMPLETED) -> Phải là màu xanh lá
    assert ui.tbl_po_master.item(0, 4).text() == "Hoàn thành"
    assert ui.tbl_po_master.item(0, 4).foreground().color() == Qt.GlobalColor.darkGreen

    # Dòng 1 (CANCELLED) -> Phải là màu đỏ và in đậm
    assert ui.tbl_po_master.item(1, 4).text() == "Đã hủy"
    assert ui.tbl_po_master.item(1, 4).foreground().color() == Qt.GlobalColor.red
    assert ui.tbl_po_master.item(1, 4).font().bold() is True

    # TC_Post_03: Khung Detail bên phải PHẢI BỊ XÓA TRẮNG
    assert ui.tbl_po_details.rowCount() == 0
    assert "0 VND" in ui.lbl_detail_total_value.text()


# ==========================================
# 3. TEST UC2: XEM CHI TIẾT PHIẾU (DETAIL) VÀ QUYỀN HÀNH ĐỘNG
# ==========================================
def test_uc2_select_completed_po_loads_details_and_enables_cancel_btn(history_ui, qtbot):
    """Kiểm tra: Chọn phiếu COMPLETED -> Load chi tiết, đổi Text Meta và BẬT nút Hủy"""
    controller, ui, mock_service, _ = history_ui

    # 1. GIVEN
    controller.current_po_list = [
        PurchaseOrderMasterDTO(id=1, code="PN-001", created_at=datetime.now(), supplier_name="NCC A",
                               total_amount=50000, status="COMPLETED", note="Hàng test")
    ]
    ui.tbl_po_master.setRowCount(1)
    # Chèn Item vào để Controller tìm thấy dòng được chọn
    ui.tbl_po_master.setItem(0, 0, QTableWidgetItem("PN-001"))

    mock_service.get_details.return_value = [
        PurchaseOrderDetailDTO(product_id=10, sku="SP01", product_name="Bút", unit_name="Cây",
                               quantity=10, unit_price=5000, total_price=50000)
    ]

    # 2. WHEN
    ui.tbl_po_master.setCurrentCell(0, 0)

    # 3. THEN
    assert "PN-001" in ui.lbl_md_po_id.text()
    assert "Hàng test" in ui.lbl_md_note.text()
    assert ui.lbl_detail_total_value.text() == "50,000 VND"
    assert ui.tbl_po_details.rowCount() == 1
    assert ui.btn_cancel_po.isEnabled() is True


def test_uc2_select_cancelled_po_shows_reason_and_disables_cancel_btn(history_ui):
    """Kiểm tra: Chọn phiếu CANCELLED -> Hiển thị Lý do hủy màu đỏ và TẮT nút Hủy"""
    controller, ui, mock_service, _ = history_ui

    # 1. GIVEN
    controller.current_po_list = [
        PurchaseOrderMasterDTO(id=2, code="PN-002", created_at=datetime.now(), supplier_name="NCC B",
                               total_amount=150000, status="CANCELLED", note="Bình thường",
                               cancel_reason="Phát hiện hàng giả")
    ]
    ui.tbl_po_master.setRowCount(1)
    ui.tbl_po_master.setItem(0, 0, QTableWidgetItem("PN-002"))

    mock_service.get_details.return_value = []

    # 2. WHEN
    ui.tbl_po_master.setCurrentCell(0, 0)

    # 3. THEN
    assert "color:red;" in ui.lbl_md_note.text()
    assert "LÝ DO HỦY:" in ui.lbl_md_note.text()
    assert "Phát hiện hàng giả" in ui.lbl_md_note.text()
    assert ui.btn_cancel_po.isEnabled() is False


# ==========================================
# 4. TEST UC4: XUẤT EXCEL CHI TIẾT PHIẾU
# ==========================================

def test_uc4_export_excel_success(history_ui, mocker):
    """Kiểm tra: Bấm xuất -> Chọn đường dẫn -> Xuất thành công -> Hiện thông báo thành công (TC_Post_01)"""
    controller, ui, mock_service, _ = history_ui

    # 1. GIVEN: Có dữ liệu (Giả lập đã chọn 1 phiếu)
    controller.selected_po_master = PurchaseOrderMasterDTO(
        id=1, code="PN-001", created_at=datetime.now(), supplier_name="NCC A",
        total_amount=50000, status="COMPLETED"
    )
    controller.current_po_details = [
        PurchaseOrderDetailDTO(product_id=10, sku="SP01", product_name="Bút", unit_name="Cây", quantity=1,
                               unit_price=1000, total_price=1000)]

    # 2. MOCKING:
    # Khống chế QFileDialog trả về 1 đường dẫn giả
    mock_file_dialog = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.QFileDialog.getSaveFileName")
    mock_file_dialog.return_value = ("/tmp/test_export.xlsx", "Excel Files (*.xlsx)")

    # Khống chế hàm Xuất Excel trả về True (Thành công)
    mock_exporter = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.PoHistoryExcelExporter.export_detail")
    mock_exporter.return_value = True

    # Khống chế QMessageBox để không hiện popup thật
    mock_msg_box = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.QMessageBox.information")

    # 3. WHEN: Bấm nút xuất
    controller.handle_export_excel()

    # 4. THEN:
    # - Đảm bảo exporter được gọi đúng đường dẫn
    mock_exporter.assert_called_once_with("/tmp/test_export.xlsx", controller.selected_po_master,
                                          controller.current_po_details)
    # - Đảm bảo hiện thông báo thành công
    mock_msg_box.assert_called_once()


def test_uc4_export_excel_failure(history_ui, mocker):
    """Kiểm tra: Xuất lỗi (ghi file thất bại) -> Hiện thông báo lỗi (TC_Inv_02)"""
    controller, ui, mock_service, _ = history_ui

    controller.selected_po_master = PurchaseOrderMasterDTO(id=1, code="PN-001", created_at=datetime.now(),
                                                           supplier_name="NCC", total_amount=50000, status="COMPLETED")
    controller.current_po_details = ["something"]

    # Mock xuất file thất bại
    mocker.patch("app.modules.inventory.ui.controllers.inventory_history_controller.QFileDialog.getSaveFileName",
                 return_value=("/tmp/fail.xlsx", ""))
    mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.PoHistoryExcelExporter.export_detail",
        return_value=False)
    mock_msg_box = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.QMessageBox.critical")

    # WHEN
    controller.handle_export_excel()

    # THEN: Phải hiện thông báo lỗi (Critical)
    mock_msg_box.assert_called_once()


def test_uc4_export_excel_cancelled(history_ui, mocker):
    """Kiểm tra: Bấm xuất -> Người dùng ấn Cancel tại Hộp thoại chọn file -> Không gọi Service (TC_Pre_02)"""
    controller, ui, mock_service, _ = history_ui

    controller.selected_po_master = PurchaseOrderMasterDTO(id=1, code="PN-001", created_at=datetime.now(),
                                                           supplier_name="NCC", total_amount=50000, status="COMPLETED")
    controller.current_po_details = ["data"]

    # Mock người dùng chọn "Cancel" (trả về đường dẫn rỗng)
    mocker.patch("app.modules.inventory.ui.controllers.inventory_history_controller.QFileDialog.getSaveFileName",
                 return_value=("", ""))
    mock_exporter = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.PoHistoryExcelExporter.export_detail")

    # WHEN
    controller.handle_export_excel()

    # THEN: Exporter không được gọi
    mock_exporter.assert_not_called()


def test_ui_cancel_action_shows_warning_box_on_validation_exception(history_ui, mocker):
    """
    TC_UI_01: Đánh chặn vi phạm chính sách kho (Kho âm / Đã bán).
    Kiểm chứng: Khi Service ném ValidationException, UI phải dùng QMessageBox.warning để cảnh báo kế toán.
    """
    controller, ui, mock_service, _ = history_ui

    # Giả lập đã chọn 1 phiếu nhập COMPLETED trên bảng giao diện
    controller.selected_po_master = PurchaseOrderMasterDTO(
        id=1, code="PO-999", created_at=datetime.now(), supplier_name="NCC A", total_amount=50000, status="COMPLETED"
    )

    # 1. MOCKING THAO TÁC NGƯỜI DÙNG:
    # Giả lập kế toán gõ lý do: "Nhập trùng đơn" và nhấn OK
    mocker.patch("app.modules.inventory.ui.controllers.inventory_history_controller.QInputDialog.getText",
                 return_value=("Nhập trùng đơn", True))

    # Gây lỗi chặn nghiệp vụ từ tầng Service đẩy lên
    mock_service.cancel_purchase_order.side_effect = ValidationException(
        "Hủy phiếu nhập sẽ làm kho bị âm, vi phạm chính sách!")

    # Khống chế QMessageBox để không bật giao diện thật khi test chạy tự động
    mock_warning_box = mocker.patch(
        "app.modules.inventory.ui.controllers.inventory_history_controller.QMessageBox.warning")

    # 2. WHEN: Kích hoạt sự kiện bấm nút Hủy phiếu trên UI
    controller.handle_cancel_po()

    # 3. THEN: Kiểm chứng giao diện phản hồi chuẩn xác
    mock_service.cancel_purchase_order.assert_called_once_with(1, "Nhập trùng đơn")
    # Đảm bảo hiển thị dạng Cảnh báo (warning) chứ không hiển thị dạng Lỗi hệ thống (critical)
    mock_warning_box.assert_called_once_with(None, "Chặn Nghiệp Vụ",
                                             "Hủy phiếu nhập sẽ làm kho bị âm, vi phạm chính sách!")
import traceback
from datetime import datetime
from decimal import Decimal
from typing import Optional
from PyQt6.QtWidgets import QWidget, QHeaderView, QAbstractItemView, QMessageBox, QTableWidgetItem, QInputDialog, \
    QLineEdit
from PyQt6.QtCore import Qt

from app.modules.tax.ui.generated.ui_tax_management import Ui_TaxManagementWidget
from app.modules.tax.services.tax_service import ITaxService
from app.modules.tax.dtos.tax_dto import YearlyTaxReportDTO
from app.modules.tax.utils.ui_helper import TaxUIHelper


class TaxManagementController(QWidget):
    def __init__(self, tax_service: ITaxService, setting_service):
        super().__init__()
        self.ui = Ui_TaxManagementWidget()
        self.ui.setupUi(self)

        self.tax_service = tax_service
        self.setting_service = setting_service

        self.selected_ledger_id: Optional[int] = None
        self.selected_ledger_year: Optional[int] = None
        self.current_operating_year = datetime.now().year

        self.setup_ui_custom()
        self.bind_events()

        # Nạp dữ liệu mặc định lúc khởi chạy phân hệ
        self.load_data_for_year(self.current_operating_year)
        self.load_history_master_table()

    def setup_ui_custom(self):
        """Đồng bộ dãn đều kích thước các cột bảng tủ kín màn hình bằng cơ chế Stretch bản địa"""
        self.ui.tbl_monthly_tax.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_tax_history_master.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_ledger_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for tbl in [self.ui.tbl_tax_history_master, self.ui.tbl_ledger_details, self.ui.tbl_monthly_tax]:
            tbl.verticalHeader().setVisible(False)
            tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.ui.spn_threshold.setGroupSeparatorShown(True)
        self.ui.frame_config.setEnabled(True)
        self.ui.splitter_invoice.setStretchFactor(0, 1)
        self.ui.splitter_invoice.setStretchFactor(1, 1)
        self.ui.splitter_invoice.setSizes([700, 700])

    def bind_events(self):
        self.ui.tabWidget_tax.currentChanged.connect(self.handle_tab_changed)
        self.ui.cbo_pit_method.currentTextChanged.connect(self.handle_live_recalculation)
        self.ui.spn_threshold.valueChanged.connect(self.handle_live_recalculation)
        self.ui.spn_vat_rate.valueChanged.connect(self.handle_live_recalculation)
        self.ui.spn_pit_rate.valueChanged.connect(self.handle_live_recalculation)

        self.ui.btn_apply_config.clicked.connect(self.handle_stage_temporary_ledger)
        self.ui.tbl_tax_history_master.itemSelectionChanged.connect(self.handle_master_row_selected)
        self.ui.btn_close_ledger.clicked.connect(self.handle_finalize_and_lock_ledger)

    def handle_tab_changed(self, index: int):
        if index == 0:
            self.load_data_for_year(self.current_operating_year)
        elif index == 1:
            self.load_history_master_table()
            # Dọn dẹp sạch sẽ vết dữ liệu hiển thị cũ bên Khung Detail phải
            self.ui.tbl_ledger_details.setRowCount(0)
            self.ui.lbl_md_ledger_year.setText("<b>Năm quyết toán:</b> --")
            self.ui.lbl_detail_total_value.setText("0 VND")
            self.ui.lbl_md_ledger_status.setText("<b>Trạng thái bảo mật:</b> --")
            self.ui.lbl_md_threshold.setText("<b>Ngưỡng miễn thuế:</b> --")
            self.ui.lbl_md_method.setText("<b>Phương pháp TNCN:</b> --")
            self.ui.lbl_md_vat_rate.setText("<b>Thuế suất GTGT:</b> --")
            self.ui.lbl_md_pit_rate.setText("<b>Thuế suất TNCN:</b> --")
            self.ui.btn_close_ledger.setEnabled(False)

    def handle_live_recalculation(self):
        """Tính toán live và đồng bộ chuỗi text công thức động lên nhãn chữ (ĐÃ XÓA SỐ CỨNG PHÂN KHÚC)"""
        try:
            year = self.current_operating_year
            threshold = Decimal(str(self.ui.spn_threshold.value()))
            vat = Decimal(str(self.ui.spn_vat_rate.value()))
            pit = Decimal(str(self.ui.spn_pit_rate.value()))
            method_text = self.ui.cbo_pit_method.currentText()
            pit_method = "FLAT_RATE" if method_text == "Khoán % doanh thu" else "BOOKKEEPING"

            # Cập nhật chuỗi text công thức động phản ứng theo tương tác thời gian thực
            self.ui.lbl_vat_formula.setText(f"📝 Công thức: Thuế GTGT = Tổng doanh thu × {vat}%")
            if pit_method == "FLAT_RATE":
                self.ui.lbl_pit_formula.setText(f"📝 Công thức: Thuế TNCN = (Doanh thu - {threshold:,.0f}) × {pit}%")
            else:
                self.ui.lbl_pit_formula.setText(f"📝 Công thức: Thuế TNCN = (Doanh thu - Chi phí) × {pit}%")

            # Thực thi thuật toán sinh báo cáo live
            report = self.tax_service.generate_yearly_tax_report_live(year, threshold, vat, pit, pit_method)

            self.ui.val_total_revenue.setText(f"{report.total_revenue:,.0f} VND")
            self.ui.val_total_tax.setText(f"{report.total_tax_amount:,.0f} VND")

            # : Đọc mốc phân khúc quy mô ngầm động từ database, không sử dụng số cứng
            limit_mid, limit_large = self.tax_service.get_tax_scale_limits()

            # Cập nhật Thẻ trạng thái phân khúc phản ứng theo mốc động hệ thống
            if report.total_revenue <= threshold:
                self.ui.val_tax_status.setText("MIỄN THUẾ")
                self.ui.val_tax_status.setStyleSheet("color: #10b981; font-weight: 800; font-size: 20px;")
            elif report.total_revenue <= limit_mid:
                self.ui.val_tax_status.setText("QUY MÔ VỪA - TỰ CHỌN")
                self.ui.val_tax_status.setStyleSheet("color: #f59e0b; font-weight: 800; font-size: 20px;")
            else:
                self.ui.val_tax_status.setText("QUY MÔ LỚN - SỔ SÁCH")
                self.ui.val_tax_status.setStyleSheet("color: #ef4444; font-weight: 800; font-size: 20px;")

            # Làm mới thanh tiến độ đồ họa
            self.ui.bar_threshold.setMaximum(100)
            if report.total_revenue <= threshold:
                percent = 0 if threshold == 0 else int((report.total_revenue / threshold) * 100)
                self.ui.bar_threshold.setValue(percent)
                self.ui.bar_threshold.setFormat(f"Vùng an toàn: {report.total_revenue:,.0f} / {threshold:,.0f} VND")
            else:
                self.ui.bar_threshold.setValue(100)
                self.ui.bar_threshold.setFormat(f"Vượt ngưỡng an toàn: {report.total_revenue:,.0f} VND")
            self.ui.bar_threshold.setStyleSheet(TaxUIHelper.generate_progress_bar_css(report.total_revenue, threshold))

            self.update_monthly_table(report)

        except Exception as e:
            traceback.print_exc()


    def handle_stage_temporary_ledger(self):
        try:
            year = self.current_operating_year
            threshold = Decimal(str(self.ui.spn_threshold.value()))
            vat = Decimal(str(self.ui.spn_vat_rate.value()))
            pit = Decimal(str(self.ui.spn_pit_rate.value()))
            method_text = self.ui.cbo_pit_method.currentText()
            pit_method = "FLAT_RATE" if method_text == "Khoán % doanh thu" else "BOOKKEEPING"

            confirm_msg = (
                f"<b>XÁC NHẬN KẾT XUẤT CHỨNG TỪ SỔ CÁI (BẢN NHÁP)</b><br><br>"
                f"Hệ thống sẽ chuyển dữ liệu năm {year} sang Sổ cái lịch sử với các thông số bạn đã cấu hình:<br>"
                f"• Mức miễn thuế cơ sở: <b>{threshold:,.0f} VND</b><br>"
                f"• Phương pháp tính thuế TNCN: <b>{method_text}</b><br>"
                f"• Thuế suất GTGT áp dụng: <b>{vat}%</b><br>"
                f"• Thuế suất TNCN áp dụng: <b>{pit}%</b><br><br>"
                f"Bạn có chắc chắn muốn kết xuất dữ liệu này sang Tab Lịch sử không?"
            )

            reply = QMessageBox.question(
                self, "Xác nhận kết xuất dữ liệu", confirm_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No: return

            if self.tax_service.stage_temporary_ledger(year, threshold, vat, pit, pit_method):
                QMessageBox.information(self, "Thành công",
                                        f"Đã kết xuất dữ liệu và đóng gói cấu hình năm {year} vào Header chứng từ nháp thành công!")
            else:
                QMessageBox.warning(self, "Bị từ chối",
                                    f"Kỳ tính thuế năm {year} đã khóa sổ (CLOSED) bằng mã PIN, không cho phép ghi đè số liệu.")
        except Exception as e:
            traceback.print_exc()

    def load_data_for_year(self, year: int):
        try:
            ledger_draft = self.tax_service.get_active_draft_ledger_config(year)

            self.ui.spn_threshold.blockSignals(True)
            self.ui.spn_vat_rate.blockSignals(True)
            self.ui.cbo_pit_method.blockSignals(True)
            self.ui.spn_pit_rate.blockSignals(True)

            if ledger_draft:
                self.ui.spn_threshold.setValue(float(ledger_draft.threshold_amount))
                self.ui.spn_vat_rate.setValue(float(ledger_draft.vat_percent))
                self.ui.cbo_pit_method.setCurrentText(
                    "Khoán % doanh thu" if ledger_draft.pit_method == "FLAT_RATE" else "Sổ sách kế toán")
                self.ui.spn_pit_rate.setValue(float(ledger_draft.pit_percent))
            else:
                self.ui.spn_threshold.setValue(1000000000.0)
                self.ui.spn_vat_rate.setValue(1.0)
                self.ui.cbo_pit_method.setCurrentText("Khoán % doanh thu")
                self.ui.spn_pit_rate.setValue(0.5)

            self.ui.spn_threshold.blockSignals(False)
            self.ui.spn_vat_rate.blockSignals(False)
            self.ui.cbo_pit_method.blockSignals(False)
            self.ui.spn_pit_rate.blockSignals(False)

            self.handle_live_recalculation()
        except Exception as e:
            traceback.print_exc()

    def load_history_master_table(self):
        try:
            ledgers = self.tax_service.get_all_ledgers()
            self.ui.tbl_tax_history_master.setRowCount(len(ledgers))

            for idx, ledger in enumerate(ledgers):
                # Cột 0: Năm tài chính
                year_item = QTableWidgetItem(str(ledger.apply_year))
                year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_tax_history_master.setItem(idx, 0, year_item)

                # Cột 1: Tổng doanh thu
                rev_item = TaxUIHelper.create_numeric_item(ledger.total_revenue)
                rev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_tax_history_master.setItem(idx, 1, rev_item)

                # Cột 2: Tổng chi phí
                cost_item = TaxUIHelper.create_numeric_item(ledger.total_cost)
                cost_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_tax_history_master.setItem(idx, 2, cost_item)

                # Cột 3: Tổng thuế đã nộp
                tax_item = TaxUIHelper.create_numeric_item(ledger.final_vat_amount + ledger.final_pit_amount)
                tax_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_tax_history_master.setItem(idx, 3, tax_item)

                # Cột 4: Trạng thái đóng khóa sổ
                status_item = QTableWidgetItem("Bản nháp" if ledger.status == "DRAFT" else "🔒 Đã khóa sổ")
                status_item.setForeground(
                    Qt.GlobalColor.blue if ledger.status == "CLOSED" else Qt.GlobalColor.darkYellow)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # ✅ Sửa từ AlignRight thành AlignCenter
                self.ui.tbl_tax_history_master.setItem(idx, 4, status_item)

                # =========================================================================
                # Cơ chế Master Cache: Lưu trữ Meta dữ liệu chạy ngầm dưới ô
                # =========================================================================
                self.ui.tbl_tax_history_master.item(idx, 0).setData(Qt.ItemDataRole.UserRole, ledger.id)
                self.ui.tbl_tax_history_master.item(idx, 1).setData(Qt.ItemDataRole.UserRole, ledger.threshold_amount)
                self.ui.tbl_tax_history_master.item(idx, 2).setData(Qt.ItemDataRole.UserRole, ledger.pit_method)
                self.ui.tbl_tax_history_master.item(idx, 3).setData(Qt.ItemDataRole.UserRole, ledger.vat_percent)
                self.ui.tbl_tax_history_master.item(idx, 4).setData(Qt.ItemDataRole.UserRole, ledger.pit_percent)
                self.ui.tbl_tax_history_master.item(idx, 0).setData(Qt.ItemDataRole.UserRole + 1, ledger.finalized_at)

        except Exception as e:
            traceback.print_exc()

    def handle_master_row_selected(self):
        """Luồng tương tác Master-Detail phản ứng nhanh từ Cache, điền thông số cấu hình đóng băng lên Header Tab 2"""
        selected_rows = self.ui.tbl_tax_history_master.selectedItems()
        if not selected_rows: return
        try:
            row_idx = selected_rows[0].row()
            self.selected_ledger_id = self.ui.tbl_tax_history_master.item(row_idx, 0).data(Qt.ItemDataRole.UserRole)
            self.selected_ledger_year = int(self.ui.tbl_tax_history_master.item(row_idx, 0).text())

            # Trích xuất bộ thông số đóng băng từ Cache
            threshold_val = self.ui.tbl_tax_history_master.item(row_idx, 1).data(Qt.ItemDataRole.UserRole)
            method_val = self.ui.tbl_tax_history_master.item(row_idx, 2).data(Qt.ItemDataRole.UserRole)
            vat_val = self.ui.tbl_tax_history_master.item(row_idx, 3).data(Qt.ItemDataRole.UserRole)
            pit_val = self.ui.tbl_tax_history_master.item(row_idx, 4).data(Qt.ItemDataRole.UserRole)
            finalized_at = self.ui.tbl_tax_history_master.item(row_idx, 0).data(Qt.ItemDataRole.UserRole + 1)
            status_text = self.ui.tbl_tax_history_master.item(row_idx, 4).text()

            # Đổ dữ liệu đóng băng cứng lên 4 nhãn thông tin Header mới của Tab 2
            method_display = "Khoán % doanh thu" if method_val == "FLAT_RATE" else "Sổ sách kế toán"
            self.ui.lbl_md_threshold.setText(f"<b>Ngưỡng miễn thuế:</b> {threshold_val:,.0f} VND")
            self.ui.lbl_md_method.setText(f"<b>Phương pháp TNCN:</b> {method_display}")
            self.ui.lbl_md_vat_rate.setText(f"<b>Thuế suất GTGT:</b> {vat_val}%")
            self.ui.lbl_md_pit_rate.setText(f"<b>Thuế suất TNCN:</b> {pit_val}%")

            # Đổ dữ liệu bảng chi tiết 12 tháng lịch sử
            details = self.tax_service.get_ledger_details(self.selected_ledger_id)
            self.ui.tbl_ledger_details.setRowCount(12)
            total_tax_frozen = Decimal('0')
            for idx, detail in enumerate(details):
                self.ui.tbl_ledger_details.setItem(idx, 0, QTableWidgetItem(f"Tháng {detail.month}"))
                self.ui.tbl_ledger_details.setItem(idx, 1, TaxUIHelper.create_numeric_item(detail.revenue))
                self.ui.tbl_ledger_details.setItem(idx, 2, TaxUIHelper.create_numeric_item(detail.cost))
                self.ui.tbl_ledger_details.setItem(idx, 3, TaxUIHelper.create_numeric_item(detail.vat_amount))
                self.ui.tbl_ledger_details.setItem(idx, 4, TaxUIHelper.create_numeric_item(detail.pit_amount))
                total_tax_frozen += (detail.vat_amount + detail.pit_amount)

            self.ui.lbl_md_ledger_year.setText(f"<b>Năm quyết toán:</b> {self.selected_ledger_year}")
            self.ui.lbl_detail_total_value.setText(f"{total_tax_frozen:,.0f} VND")

            if finalized_at:
                if isinstance(finalized_at, datetime):
                    date_str = finalized_at.strftime("%d/%m/%Y %H:%M")
                else:
                    date_str = str(finalized_at)
                self.ui.lbl_md_ledger_date.setText(f"<b>Ngày khóa sổ:</b> {date_str}")
            else:
                self.ui.lbl_md_ledger_date.setText("<b>Ngày khóa sổ:</b> Chưa khóa (Bản nháp)")

            if status_text == "🔒 Đã khóa sổ":
                self.ui.lbl_md_ledger_status.setText(
                    "<b>Trạng thái bảo mật:</b> <span style='color:green;'>🔒 ĐÃ KHÓA SỔ</span>")
                self.ui.btn_close_ledger.setEnabled(False)
            else:
                self.ui.lbl_md_ledger_status.setText(
                    "<b>Trạng thái bảo mật:</b> <span style='color:orange;'>⚠️ Bản nháp (Mở duyệt)</span>")
                self.ui.btn_close_ledger.setEnabled(True)
        except Exception as e:
            traceback.print_exc()

    def handle_finalize_and_lock_ledger(self):
        if not self.selected_ledger_year: return
        reply = QMessageBox.warning(
            self, "XÁC NHẬN CHỐT SỔ TÀI CHÍNH",
            f"BẠN ĐANG THỰC HIỆN KHÓA SỔ THUẾ NĂM {self.selected_ledger_year}.\n\nThao tác này sẽ ĐÓNG BĂNG VĨNH VIỄN toàn bộ số liệu. Không thể điều chỉnh sau khi chốt.\n\nBạn có chắc chắn muốn thực hiện không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No: return
        entered_pin, ok = QInputDialog.getText(self, "Xác thực bảo mật mã PIN", "Nhập mã PIN bảo vệ ứng dụng:",
                                               QLineEdit.EchoMode.Password)
        if not ok or not entered_pin: return
        if self.setting_service.verify_app_pin(entered_pin):
            if self.tax_service.close_and_freeze_ledger(self.selected_ledger_year):
                QMessageBox.information(self, "Thành công",
                                        f"🔒 Kỳ thuế năm {self.selected_ledger_year} đã đóng băng vĩnh viễn.")
                self.load_history_master_table()
                self.ui.btn_close_ledger.setEnabled(False)
                self.ui.lbl_md_ledger_status.setText(
                    "<b>Trạng thái bảo mật:</b> <span style='color:green;'>🔒 ĐÃ KHÓA SỔ</span>")
            else:
                QMessageBox.warning(self, "Thất bại", "Lỗi đóng băng dữ liệu.")
        else:
            QMessageBox.warning(self, "Lỗi bảo mật", "Mã PIN không chính xác!")

    def update_monthly_table(self, report: YearlyTaxReportDTO):
        self.ui.tbl_monthly_tax.setRowCount(12)
        for idx, month_detail in enumerate(report.monthly_details):
            self.ui.tbl_monthly_tax.setItem(idx, 0, QTableWidgetItem(f"Tháng {month_detail.month}"))
            self.ui.tbl_monthly_tax.setItem(idx, 1, TaxUIHelper.create_numeric_item(month_detail.revenue))
            self.ui.tbl_monthly_tax.setItem(idx, 2, TaxUIHelper.create_numeric_item(month_detail.vat_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 3, TaxUIHelper.create_numeric_item(month_detail.pit_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 4, TaxUIHelper.create_numeric_item(month_detail.total_tax))
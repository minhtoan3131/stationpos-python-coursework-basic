import traceback
from datetime import datetime
from decimal import Decimal
from PyQt6.QtWidgets import QWidget, QHeaderView, QAbstractItemView, QMessageBox, QTableWidgetItem

from app.modules.tax.ui.generated.ui_tax_management import Ui_TaxManagementWidget
from app.modules.tax.services.tax_service import ITaxService
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, YearlyTaxReportDTO
from app.modules.tax.utils.ui_helper import TaxUIHelper


class TaxManagementController(QWidget):
    def __init__(self, tax_service: ITaxService):
        super().__init__()
        self.ui = Ui_TaxManagementWidget()
        self.ui.setupUi(self)

        # Inject Service
        self.tax_service = tax_service

        self.setup_ui_custom()
        self.setup_year_combobox()
        self.bind_events()

        # Load dữ liệu mặc định của năm hiện tại khi mở màn hình
        current_year = datetime.now().year
        self.load_data_for_year(current_year)

    def setup_ui_custom(self):
        """Cấu hình hành vi hiển thị cho bảng dữ liệu"""
        header = self.ui.tbl_monthly_tax.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_monthly_tax.verticalHeader().setDefaultSectionSize(45)
        self.ui.tbl_monthly_tax.verticalHeader().setVisible(False)
        self.ui.tbl_monthly_tax.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def setup_year_combobox(self):
        """Khởi tạo danh sách các năm trong ComboBox"""
        current_year = datetime.now().year
        self.ui.cbo_year.blockSignals(True)  # Chặn sự kiện để không trigger load_data 2 lần
        self.ui.cbo_year.clear()

        # Hiển thị từ 2 năm trước đến 2 năm sau
        for year in range(current_year - 2, current_year + 3):
            self.ui.cbo_year.addItem(str(year))

        self.ui.cbo_year.setCurrentText(str(current_year))
        self.ui.cbo_year.blockSignals(False)

    def bind_events(self):
        """Đăng ký lắng nghe các sự kiện tương tác trên UI"""
        self.ui.btn_apply_config.clicked.connect(self.handle_apply_config)
        self.ui.cbo_year.currentTextChanged.connect(self.handle_year_changed)

    # ==========================================
    # KHU VỰC XỬ LÝ SỰ KIỆN (EVENT HANDLERS)
    # ==========================================

    def handle_year_changed(self, year_str: str):
        if not year_str:
            return
        year = int(year_str)
        self.load_data_for_year(year)

    def handle_apply_config(self):
        try:
            year = int(self.ui.cbo_year.currentText())
            current_year = datetime.now().year

            # Thêm logic cảnh báo nếu cập nhật dữ liệu của năm cũ
            if year < current_year:
                reply = QMessageBox.warning(
                    self,
                    "Cảnh báo thay đổi dữ liệu lịch sử",
                    f"Bạn đang điều chỉnh cấu hình thuế cho năm {year} (năm trong quá khứ).\n\n"
                    f"Hành động này sẽ tính toán lại toàn bộ báo cáo thuế của năm {year}. "
                    f"Nếu sổ sách kế toán của năm này đã được chốt, việc thay đổi có thể gây ra sự sai lệch số liệu.\n\n"
                    f"Bạn có chắc chắn muốn ghi đè cấu hình này không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No  # Default focus vào nút No cho an toàn
                )

                # Nếu người dùng chọn No (hoặc tắt hộp thoại), dừng việc lưu lại
                if reply == QMessageBox.StandardButton.No:
                    return

            # Nếu là năm hiện tại/tương lai, hoặc người dùng đã bấm Yes, tiến hành lưu bình thường
            threshold = Decimal(str(self.ui.spn_threshold.value()))
            vat = Decimal(str(self.ui.spn_vat_rate.value()))
            pit = Decimal(str(self.ui.spn_pit_rate.value()))

            config = TaxConfigDTO(
                apply_year=year,
                threshold_amount=threshold,
                vat_percent=vat,
                pit_percent=pit
            )

            success = self.tax_service.save_config(config)
            if success:
                QMessageBox.information(self, "Thành công", f"Đã cập nhật cấu hình thuế cho năm {year}")
                self.load_data_for_year(year)
            else:
                QMessageBox.warning(self, "Thất bại", "Không thể lưu cấu hình. Vui lòng kiểm tra lại!")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi Hệ Thống", f"Đã xảy ra lỗi khi lưu cấu hình:\n{str(e)}")

    # ==========================================
    # CẬP NHẬT DỮ LIỆU LÊN GIAO DIỆN
    # ==========================================

    def load_data_for_year(self, year: int):
        try:
            # Tải và hiển thị cấu hình (để fill vào các ô SpinBox)
            config = self.tax_service.get_or_create_config(year)
            self.update_config_inputs(config)

            # Tải và hiển thị Báo cáo Thuế
            report: YearlyTaxReportDTO = self.tax_service.generate_yearly_tax_report(year)
            self.update_kpi_cards(report)
            self.update_progress_bar(report, config.threshold_amount)
            self.update_monthly_table(report)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi Hệ Thống", f"Không thể tải dữ liệu báo cáo thuế:\n{str(e)}")

    def update_config_inputs(self, config: TaxConfigDTO):
        self.ui.spn_threshold.setValue(float(config.threshold_amount))
        self.ui.spn_vat_rate.setValue(float(config.vat_percent))
        self.ui.spn_pit_rate.setValue(float(config.pit_percent))

    def update_kpi_cards(self, report: YearlyTaxReportDTO):
        self.ui.val_total_revenue.setText(f"{report.total_revenue:,.0f} VND")
        self.ui.val_total_tax.setText(f"{report.total_tax_amount:,.0f} VND")

        if report.is_over_threshold:
            self.ui.val_tax_status.setText("ĐÃ VƯỢT NGƯỠNG")
            self.ui.val_tax_status.setStyleSheet("color: #ef4444; font-weight: 800; font-size: 24px;")
        else:
            self.ui.val_tax_status.setText("DƯỚI NGƯỠNG")
            self.ui.val_tax_status.setStyleSheet("color: #10b981; font-weight: 800; font-size: 24px;")

    def update_progress_bar(self, report: YearlyTaxReportDTO, threshold: Decimal):
        bar = self.ui.bar_threshold
        total = report.total_revenue

        # Update text và value (Logic hiển thị)
        if total <= threshold:
            # Dưới ngưỡng: Quy đổi ra thang 100%
            percent = 0 if threshold == 0 else int((total / threshold) * 100)
            bar.setMaximum(100)
            bar.setValue(percent)
            bar.setFormat(f"Vùng an toàn: {total:,.0f} / {threshold:,.0f} VND")
        else:
            # Vượt ngưỡng: Cho thanh full 100%
            bar.setMaximum(100)
            bar.setValue(100)
            over_amount = total - threshold
            bar.setFormat(f"Vượt ngưỡng: +{over_amount:,.0f} VND")

        # Render CSS bằng Utility class
        css = TaxUIHelper.generate_progress_bar_css(total, threshold)
        bar.setStyleSheet(css)

    def update_monthly_table(self, report: YearlyTaxReportDTO):
        self.ui.tbl_monthly_tax.setRowCount(12)

        for idx, month_detail in enumerate(report.monthly_details):
            # Tháng
            month_item = QTableWidgetItem(f"Tháng {month_detail.month}")
            self.ui.tbl_monthly_tax.setItem(idx, 0, month_item)

            # Sử dụng UI Helper để format tiền
            self.ui.tbl_monthly_tax.setItem(idx, 1, TaxUIHelper.create_numeric_item(month_detail.revenue))
            self.ui.tbl_monthly_tax.setItem(idx, 2, TaxUIHelper.create_numeric_item(month_detail.vat_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 3, TaxUIHelper.create_numeric_item(month_detail.pit_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 4, TaxUIHelper.create_numeric_item(month_detail.total_tax))
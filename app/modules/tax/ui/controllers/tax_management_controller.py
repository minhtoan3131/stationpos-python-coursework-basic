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
        """Cấu hình hành vi hiển thị cho bảng dữ liệu và thiết lập sự kiện mới"""
        header = self.ui.tbl_monthly_tax.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_monthly_tax.verticalHeader().setDefaultSectionSize(45)
        self.ui.tbl_monthly_tax.verticalHeader().setVisible(False)
        self.ui.tbl_monthly_tax.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Bước 5: Kết nối sự kiện thay đổi phương pháp thuế TNCN điện tử
        self.ui.cbo_pit_method.currentTextChanged.connect(self.handle_pit_method_changed)

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

    def handle_pit_method_changed(self, text: str):
        """Luồng 2: Xử lý tương tác tính toán giả định thời gian thực (Interactive Simulator)"""
        if not text:
            return

        try:
            year = int(self.ui.cbo_year.currentText())
            threshold = Decimal(str(self.ui.spn_threshold.value()))
            vat = Decimal(str(self.ui.spn_vat_rate.value()))
            pit = Decimal(str(self.ui.spn_pit_rate.value()))
            pit_method = "FLAT_RATE" if text == "Khoán % doanh thu" else "BOOKKEEPING"

            # Đóng gói cấu hình mô phỏng nhanh của người dùng
            config = TaxConfigDTO(
                apply_year=year,
                threshold_amount=threshold,
                vat_percent=vat,
                pit_percent=pit,
                pit_method=pit_method
            )

            # Ghi nhận nhanh cấu hình thay đổi tạm thời xuống Service lớp dưới
            self.tax_service.save_config(config)

            # Đổ lại dữ liệu tính toán mới lên bảng báo cáo và thẻ KPI ngay lập tức
            report = self.tax_service.generate_yearly_tax_report(year)
            self.update_kpi_cards(report)
            self.update_progress_bar(report, config.threshold_amount)
            self.update_monthly_table(report)

        except Exception as e:
            traceback.print_exc()

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

                if reply == QMessageBox.StandardButton.No:
                    return

            threshold = Decimal(str(self.ui.spn_threshold.value()))
            vat = Decimal(str(self.ui.spn_vat_rate.value()))
            pit = Decimal(str(self.ui.spn_pit_rate.value()))

            # Trích xuất phương pháp tính thuế TNCN từ UI ComboBox mới
            pit_method = "FLAT_RATE" if self.ui.cbo_pit_method.currentText() == "Khoán % doanh thu" else "BOOKKEEPING"

            config = TaxConfigDTO(
                apply_year=year,
                threshold_amount=threshold,
                vat_percent=vat,
                pit_percent=pit,
                pit_method=pit_method
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
            # 1. Tải và cấu hình thông số đầu vào cơ sở
            config = self.tax_service.get_or_create_config(year)
            self.update_config_inputs(config)

            # 2. Tải dữ liệu Báo cáo Thuế tổng quát của năm
            report: YearlyTaxReportDTO = self.tax_service.generate_yearly_tax_report(year)

            # 3. Luồng 1: Kiểm tra phân khúc quy mô doanh thu để điều phối hoạt động Combo-box
            total_revenue = report.total_revenue
            self.ui.cbo_pit_method.blockSignals(True)  # Chặn loop signal khi thay đổi chương trình

            if total_revenue > Decimal('3000000000'):
                self.ui.cbo_pit_method.setCurrentText("Sổ sách kế toán")
                self.ui.cbo_pit_method.setEnabled(False)
                # Đóng băng hiển thị thuế suất cố định theo luật quy mô lớn
                self.ui.spn_pit_rate.setValue(17.0 if total_revenue <= Decimal('50000000000') else 20.0)
                self.ui.spn_pit_rate.setEnabled(False)
            elif total_revenue <= Decimal('1000000000'):
                self.ui.cbo_pit_method.setEnabled(False)
                self.ui.spn_pit_rate.setValue(0.0)
                self.ui.spn_pit_rate.setEnabled(False)
            else:
                self.ui.cbo_pit_method.setEnabled(True)
                self.ui.spn_pit_rate.setEnabled(True)
                if config.pit_method == "FLAT_RATE":
                    self.ui.cbo_pit_method.setCurrentText("Khoán % doanh thu")
                    self.ui.spn_pit_rate.setValue(float(config.pit_percent))
                else:
                    self.ui.cbo_pit_method.setCurrentText("Sổ sách kế toán")
                    self.ui.spn_pit_rate.setValue(15.0)  # Tự nhảy lên 15% trực quan khi sang Sổ sách

            self.ui.cbo_pit_method.blockSignals(False)

            # 4. Đổ dữ liệu đồ họa trực quan lên các thành phần UI còn lại
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

        # Nâng cấp 3 trạng thái KPI định vị thương hiệu quy mô của HKD theo luật 2026
        if report.total_revenue <= Decimal('1000000000'):
            self.ui.val_tax_status.setText("MIỄN THUẾ")
            self.ui.val_tax_status.setStyleSheet("color: #10b981; font-weight: 800; font-size: 20px;")
        elif report.total_revenue <= Decimal('3000000000'):
            self.ui.val_tax_status.setText("QUY MÔ VỪA - TỰ CHỌN")
            self.ui.val_tax_status.setStyleSheet("color: #f59e0b; font-weight: 800; font-size: 20px;")
        else:
            self.ui.val_tax_status.setText("QUY MÔ LỚN - SỔ SÁCH")
            self.ui.val_tax_status.setStyleSheet("color: #ef4444; font-weight: 800; font-size: 20px;")

    def update_progress_bar(self, report: YearlyTaxReportDTO, threshold: Decimal):
        bar = self.ui.bar_threshold
        total = report.total_revenue

        # Nâng cấp hiển thị các vạch mốc cảnh báo giới hạn quy mô pháp lý quan trọng
        if total <= threshold:
            percent = 0 if threshold == 0 else int((total / threshold) * 100)
            bar.setMaximum(100)
            bar.setValue(percent)
            bar.setFormat(f"Vùng an toàn: {total:,.0f} / {threshold:,.0f} VND")
        elif total <= Decimal('3000000000'):
            bar.setMaximum(100)
            bar.setValue(100)
            bar.setFormat(f"Vùng tự chọn thuế: {total:,.0f} VND (Mốc bắt buộc sổ sách: 3 Tỷ)")
        else:
            bar.setMaximum(100)
            bar.setValue(100)
            bar.setFormat(f"Bắt buộc kế toán sổ sách: Vượt ngưỡng quy mô +{total - Decimal('3000000000'):,.0f} VND")

        # Render CSS bằng Utility class
        css = TaxUIHelper.generate_progress_bar_css(total, threshold)
        bar.setStyleSheet(css)

    def update_monthly_table(self, report: YearlyTaxReportDTO):
        self.ui.tbl_monthly_tax.setRowCount(12)

        for idx, month_detail in enumerate(report.monthly_details):
            month_item = QTableWidgetItem(f"Tháng {month_detail.month}")
            self.ui.tbl_monthly_tax.setItem(idx, 0, month_item)

            self.ui.tbl_monthly_tax.setItem(idx, 1, TaxUIHelper.create_numeric_item(month_detail.revenue))
            self.ui.tbl_monthly_tax.setItem(idx, 2, TaxUIHelper.create_numeric_item(month_detail.vat_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 3, TaxUIHelper.create_numeric_item(month_detail.pit_amount))
            self.ui.tbl_monthly_tax.setItem(idx, 4, TaxUIHelper.create_numeric_item(month_detail.total_tax))
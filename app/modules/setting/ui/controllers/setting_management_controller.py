from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import QTime, Qt
from app.modules.setting.ui.generated.ui_setting_widget import Ui_SettingWidget
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO


class SettingManagementController(QWidget):
    def __init__(self, store_config_service, security_service, backup_service):
        super().__init__()
        self.store_config_service = store_config_service
        self.security_service = security_service
        self.backup_service = backup_service

        # Cờ hiệu chống tín hiệu trễ
        self.is_loading = False

        # Bộ nhớ đệm lưu trạng thái gốc dưới DB
        self.baseline_store = {}
        self.baseline_backup = {}

        self.ui = Ui_SettingWidget()
        self.ui.setupUi(self)

        self.apply_disabled_stylesheets()
        self.bind_events()
        self.bind_change_signals()

    def apply_disabled_stylesheets(self):
        """
        Ghi đè Stylesheet để bổ sung trạng thái :disabled (ẩn mờ).
        Nếu không có đoạn này, Qt sẽ giữ nguyên màu xanh rực kể cả khi setEnabled(False).
        """
        disabled_style = """
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;   /* Màu nền xám nhạt */
                color: #94a3b8;              /* Chữ xám mờ */
                border: 1px solid #cbd5e1;   /* Viền xám nhẹ */
            }
        """
        self.ui.btn_save_bill.setStyleSheet(disabled_style)
        self.ui.btn_save_backup_config.setStyleSheet(disabled_style)

    def bind_events(self):
        self.ui.btn_save_bill.clicked.connect(self.handle_save_bill_info)
        self.ui.btn_save_security.clicked.connect(self.handle_save_security)
        self.ui.btn_save_backup_config.clicked.connect(self.handle_save_backup_config)
        self.ui.btn_browse_path.clicked.connect(self.handle_browse_backup_path)
        self.ui.btn_manual_backup.clicked.connect(self.handle_manual_backup)
        self.ui.btn_restore_backup.clicked.connect(self.handle_restore_backup)

    def bind_change_signals(self):
        # Lắng nghe thông tin hóa đơn
        self.ui.txt_ten.textChanged.connect(self.check_store_changes)
        self.ui.txt_sdt.textChanged.connect(self.check_store_changes)
        self.ui.txt_diachi.textChanged.connect(self.check_store_changes)
        self.ui.txt_loichao.textChanged.connect(self.check_store_changes)
        self.ui.cb_giay.currentIndexChanged.connect(self.check_store_changes)

        # Lắng nghe thông số sao lưu
        self.ui.chk_toggle.toggled.connect(self.check_backup_changes)
        self.ui.time_backup.timeChanged.connect(self.check_backup_changes)
        self.ui.txt_backup_path.textChanged.connect(self.check_backup_changes)

    def load_current_settings(self):
        """Kéo dữ liệu từ DB lên và thiết lập trạng thái đóng băng ban đầu"""
        # BẬT CỜ HIỆU: Đang trong quá trình nạp dữ liệu hệ thống
        self.is_loading = True

        store_config = self.store_config_service.get_store_config()
        backup_config = self.backup_service.get_backup_config()

        # 1. Chụp ảnh lưu trạng thái gốc ban đầu (Baseline)
        self.baseline_store = {
            'name': store_config.name,
            'phone': store_config.phone,
            'address': store_config.address,
            'footer': store_config.footer,
            'paper_size': store_config.paper_size
        }
        self.baseline_backup = {
            'auto_enabled': backup_config.auto_enabled,
            'folder_path': backup_config.folder_path,
            'backup_time': backup_config.backup_time
        }

        # 2. Đổ dữ liệu lên các thành phần UI
        self.ui.txt_ten.setText(store_config.name)
        self.ui.txt_sdt.setText(store_config.phone)
        self.ui.txt_diachi.setText(store_config.address)
        self.ui.txt_loichao.setText(store_config.footer)
        self.ui.cb_giay.setCurrentIndex(1 if store_config.paper_size == 'K58' else 0)

        self.ui.txt_pin_hientai.clear()
        self.ui.txt_pin_moi.clear()
        self.ui.txt_pin_xacnhan.clear()

        self.ui.chk_toggle.setChecked(backup_config.auto_enabled)
        self.ui.txt_backup_path.setText(backup_config.folder_path)

        time_parts = backup_config.backup_time.split(":")
        if len(time_parts) == 2:
            self.ui.time_backup.setTime(QTime(int(time_parts[0]), int(time_parts[1])))

        # 3. Chủ động ép nút bấm ẩn mờ đi ngay từ đầu
        self.ui.btn_save_bill.setEnabled(False)
        self.ui.btn_save_backup_config.setEnabled(False)

        # HẠ CỜ HIỆU: Đã hoàn tất nạp dữ liệu an toàn
        self.is_loading = False

    # ==========================================
    # LOGIC KIỂM TRA BIẾN ĐỘNG CHỐNG TÍN HIỆU TRỄ
    # ==========================================
    def check_store_changes(self):
        if self.is_loading:  # Nếu đang load dữ liệu bằng code -> Bỏ qua không kiểm tra
            return

        paper_text = self.ui.cb_giay.currentText()
        paper_size = 'K58' if "K58" in paper_text else 'K80'

        is_dirty = (
                self.ui.txt_ten.text().strip() != self.baseline_store.get('name') or
                self.ui.txt_sdt.text().strip() != self.baseline_store.get('phone') or
                self.ui.txt_diachi.text().strip() != self.baseline_store.get('address') or
                self.ui.txt_loichao.text().strip() != self.baseline_store.get('footer') or
                paper_size != self.baseline_store.get('paper_size')
        )
        self.ui.btn_save_bill.setEnabled(is_dirty)

    def check_backup_changes(self):
        if self.is_loading:  # Nếu đang load dữ liệu bằng code -> Bỏ qua không kiểm tra
            return

        current_enabled = self.ui.chk_toggle.isChecked()
        current_path = self.ui.txt_backup_path.text().strip()
        current_time = self.ui.time_backup.time().toString("HH:mm")

        is_dirty = (
                current_enabled != self.baseline_backup.get('auto_enabled') or
                current_path != self.baseline_backup.get('folder_path') or
                current_time != self.baseline_backup.get('backup_time')
        )
        self.ui.btn_save_backup_config.setEnabled(is_dirty)

    # ==========================================
    # LOGIC XỬ LÝ SỰ KIỆN BẤM LƯU
    # ==========================================
    def handle_save_bill_info(self):
        name = self.ui.txt_ten.text().strip()
        phone = self.ui.txt_sdt.text().strip()
        address = self.ui.txt_diachi.text().strip()
        footer = self.ui.txt_loichao.text().strip()
        paper_text = self.ui.cb_giay.currentText()
        paper_size = 'K58' if "K58" in paper_text else 'K80'

        if not name:
            QMessageBox.warning(self, "Lỗi dữ liệu", "Tên cửa hàng không được để trống!")
            return

        config = StoreConfigDTO(name=name, phone=phone, address=address, paper_size=paper_size, footer=footer)
        if self.store_config_service.save_store_config(config):
            QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin cửa hàng thành công!")

            # Đồng bộ lại mốc so sánh và ép mờ nút lập tức
            self.baseline_store = {'name': name, 'phone': phone, 'address': address, 'footer': footer,
                                   'paper_size': paper_size}
            self.ui.btn_save_bill.setEnabled(False)

    def handle_save_backup_config(self):
        auto_enabled = self.ui.chk_toggle.isChecked()
        folder_path = self.ui.txt_backup_path.text().strip()
        backup_time = self.ui.time_backup.time().toString("HH:mm")

        if not folder_path:
            QMessageBox.warning(self, "Lỗi dữ liệu", "Vui lòng chọn thư mục lưu trữ file sao lưu!")
            return

        dto = BackupConfigDTO(auto_enabled=auto_enabled, backup_time=backup_time, folder_path=folder_path)
        if self.backup_service.save_backup_config(dto):
            QMessageBox.information(self, "Thành công", "Đã lưu cấu hình sao lưu dữ liệu tự động!")

            # Đồng bộ lại mốc so sánh và ép mờ nút lập tức
            self.baseline_backup = {'auto_enabled': auto_enabled, 'folder_path': folder_path,
                                    'backup_time': backup_time}
            self.ui.btn_save_backup_config.setEnabled(False)

    def handle_save_security(self):
        current_pin = self.ui.txt_pin_hientai.text().strip()
        new_pin = self.ui.txt_pin_moi.text().strip()
        confirm_pin = self.ui.txt_pin_xacnhan.text().strip()
        try:
            if self.security_service.change_pin(current_pin, new_pin, confirm_pin):
                QMessageBox.information(self, "Thành công", "Đã cập nhật mã PIN bảo mật hệ thống mới thành công!")
                self.ui.txt_pin_hientai.clear()
                self.ui.txt_pin_moi.clear()
                self.ui.txt_pin_xacnhan.clear()
        except ValueError as e:
            QMessageBox.warning(self, "Lỗi bảo mật", str(e))

    def handle_browse_backup_path(self):
        current_path = self.ui.txt_backup_path.text()
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu trữ Backup", current_path)
        if folder_path:
            self.ui.txt_backup_path.setText(folder_path)

    def handle_manual_backup(self):
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            saved_path = self.backup_service.execute_backup()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QMessageBox.information(self, "Sao lưu thành công",
                                    f"Hệ thống đã xuất dữ liệu an toàn thành công!\nTập tin: {saved_path}")
        except Exception as e:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QMessageBox.critical(self, "Lỗi sao lưu", str(e))

    def handle_restore_backup(self):
        confirm = QMessageBox.warning(self, "CẢNH BÁO",
                                      "Hành động này sẽ GHI ĐÈ toàn bộ dữ liệu hiện tại.\nBạn có chắc chắn muốn tiếp tục?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn tập tin cấu trúc dữ liệu khôi phục", "",
                                                   "Database Files (*.sql)")
        if not file_path: return
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            if self.backup_service.execute_restore(file_path):
                self.setCursor(Qt.CursorShape.ArrowCursor)
                QMessageBox.information(self, "Phục hồi thành công", "Cơ sở dữ liệu đã phục hồi trạng thái nguyên vẹn!")
        except Exception as e:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QMessageBox.critical(self, "Lỗi phục hồi", str(e))
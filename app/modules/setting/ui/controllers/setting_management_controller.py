from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

from app.modules.setting.ui.generated.ui_setting_widget import Ui_SettingWidget


class SettingManagementController(QWidget):
    def __init__(self, setting_service):
        super().__init__()
        self.setting_service = setting_service

        self.ui = Ui_SettingWidget()
        self.ui.setupUi(self)

        self.bind_events()

    def bind_events(self):
        """Kết nối các nút bấm trên giao diện cấu hình"""
        # Nhóm 1: Nút lưu độc lập
        self.ui.btn_save_bill.clicked.connect(self.handle_save_bill_info)
        self.ui.btn_save_security.clicked.connect(self.handle_save_security)
        self.ui.btn_save_backup_config.clicked.connect(self.handle_save_backup_config)

        # Nhóm 2: Nút hành động Backup
        self.ui.btn_browse_path.clicked.connect(self.handle_browse_backup_path)
        self.ui.btn_manual_backup.clicked.connect(self.handle_manual_backup)
        self.ui.btn_restore_backup.clicked.connect(self.handle_restore_backup)

    def handle_save_bill_info(self):
        QMessageBox.information(self, "Thành công", "Đã ghi nhận yêu cầu: Lưu thông tin hóa đơn.")

    def handle_save_security(self):
        QMessageBox.information(self, "Thành công", "Đã ghi nhận yêu cầu: Đổi mã PIN.")

    def handle_save_backup_config(self):
        QMessageBox.information(self, "Thành công", "Đã ghi nhận yêu cầu: Lưu cấu hình sao lưu tự động.")

    def handle_browse_backup_path(self):
        """Mở hộp thoại chọn thư mục cho Google Drive Desktop"""
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu trữ Backup (Drive/OneDrive)", "")
        if folder_path:
            self.ui.txt_backup_path.setText(folder_path)

    def handle_manual_backup(self):
        QMessageBox.information(self, "Tiến trình", "Hệ thống đang gọi mysqldump để xuất file...")

    def handle_restore_backup(self):
        QMessageBox.warning(self, "Cảnh báo", "Tính năng phục hồi đang được chuẩn bị.")

    def load_current_settings(self):
        """Hàm này sẽ gọi Database kéo 1 loạt Key-Value lên để điền vào Form"""
        pass
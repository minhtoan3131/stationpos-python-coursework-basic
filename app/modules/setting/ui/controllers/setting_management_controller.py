from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.ui.generated.ui_setting_widget import Ui_SettingWidget


class SettingManagementController(QWidget):
    def __init__(self, store_config_service, security_service=None, backup_service=None):
        """
        Nhận độc lập từng Service xử lý nghiệp vụ riêng biệt.
        Các Service chưa viết (như bảo mật, backup) tạm thời để mặc định là None.
        """
        super().__init__()
        self.store_config_service = store_config_service
        self.security_service = security_service
        self.backup_service = backup_service

        self.ui = Ui_SettingWidget()
        self.ui.setupUi(self)

        self.bind_events()

    def bind_events(self):
        """Kết nối các nút bấm trên giao diện cấu hình"""
        # Nhóm 1: Các nút lưu thông số
        self.ui.btn_save_bill.clicked.connect(self.handle_save_bill_info)
        self.ui.btn_save_security.clicked.connect(self.handle_save_security)
        self.ui.btn_save_backup_config.clicked.connect(self.handle_save_backup_config)

        # Nhóm 2: Các nút hành động phụ trợ
        self.ui.btn_browse_path.clicked.connect(self.handle_browse_backup_path)
        self.ui.btn_manual_backup.clicked.connect(self.handle_manual_backup)
        self.ui.btn_restore_backup.clicked.connect(self.handle_restore_backup)

    def load_current_settings(self):
        """Hàm điều phối: Đọc dữ liệu từ DB đẩy ngược lên các widget giao diện"""
        # 1. Khôi phục dữ liệu cho cụm Thông tin hóa đơn
        config = self.store_config_service.get_store_config()
        self.ui.txt_ten.setText(config.name)
        self.ui.txt_sdt.setText(config.phone)
        self.ui.txt_diachi.setText(config.address)
        self.ui.txt_loichao.setText(config.footer)

        # Đồng bộ trạng thái chọn của ComboBox khổ giấy (K80 index 0, K58 index 1)
        if config.paper_size == 'K58':
            self.ui.cb_giay.setCurrentIndex(1)
        else:
            self.ui.cb_giay.setCurrentIndex(0)

        # 2. Khôi phục dữ liệu cho cụm Bảo mật & Backup (Sẽ viết ở các bước tiếp theo)
        pass

    def handle_save_bill_info(self):
        """Thu thập dữ liệu thông tin hóa đơn và lưu qua Service chuyên trách"""
        name = self.ui.txt_ten.text().strip()
        phone = self.ui.txt_sdt.text().strip()
        address = self.ui.txt_diachi.text().strip()
        footer = self.ui.txt_loichao.text().strip()

        # Đọc text từ ComboBox và chuẩn hóa dữ liệu lưu trữ
        paper_text = self.ui.cb_giay.currentText()
        paper_size = 'K58' if "K58" in paper_text else 'K80'

        if not name:
            QMessageBox.warning(self, "Lỗi dữ liệu", "Tên cửa hàng hiển thị trên bill không được để trống!")
            self.ui.txt_ten.setFocus()
            return

        # Đóng gói dữ liệu vào DTO cục bộ của chức năng
        config = StoreConfigDTO(
            name=name,
            phone=phone,
            address=address,
            paper_size=paper_size,
            footer=footer
        )

        # Chuyển dữ liệu xuống tầng nghiệp vụ xử lý ghi nhận
        if self.store_config_service.save_store_config(config):
            QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin cửa hàng và cấu hình in ấn thành công!")


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

import sys
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication
from PyQt6.QtCore import Qt

from app.modules.setting.ui.generated.ui_lock_screen_dialog import Ui_LockScreenDialog


class LockScreenDialog(QDialog):
    def __init__(self, setting_service, parent=None):
        # Thiết lập cửa sổ độc lập, luôn nằm trên cùng và giữ thanh tiêu đề hệ thống
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setting_service = setting_service

        self.ui = Ui_LockScreenDialog()
        self.ui.setupUi(self)

        self.setModal(True)
        self._is_authenticated = False

        # Phóng to toàn màn hình ngay khi khởi tạo
        self.showMaximized()
        self.ui.main_layout.setAlignment(self.ui.center_card, Qt.AlignmentFlag.AlignCenter)
        self.bind_events()



    def bind_events(self):
        self.ui.txt_pin.returnPressed.connect(self.handle_pin_submit)
        self.ui.btn_forgot.clicked.connect(self.show_forgot_pin_notice)
        self.ui.btn_forgot.setAutoDefault(False)
        self.ui.txt_pin.setFocus()

    def closeEvent(self, event):
        """Bấm nút (X) hệ thống khi chưa nhập đúng mã PIN -> Tắt toàn bộ ứng dụng"""
        if not self._is_authenticated:
            QApplication.instance().quit()
        else:
            super().closeEvent(event)

    def keyPressEvent(self, event):
        """Ghi đè quản lý phím bấm hệ thống"""
        if event.key() == Qt.Key.Key_Escape:
            # Chặn nút Esc để không bị bypass màn hình bảo vệ
            event.ignore()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Lệnh này báo hiệu cho Qt rằng phím Enter đã được xử lý xong hoàn toàn,
            # chặn đứng hiện tượng kích hoạt nhầm nút "Quên mã PIN" sau khi tắt popup.
            event.accept()
        else:
            super().keyPressEvent(event)

    def _apply_modern_msg_style(self, msg: QMessageBox):
        """Trang trí lại giao diện phẳng hiện đại cho QMessageBox"""
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
            }
            QLabel {
                color: #1e293b;
                font-size: 14px;
                min-height: 30px;
                margin-right: 15px;
            }
            QPushButton {
                background-color: #0ea5e9;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            QPushButton:pressed {
                background-color: #0369a1;
            }
        """)

    def handle_pin_submit(self):
        entered_pin = self.ui.txt_pin.text().strip()

        if len(entered_pin) == 0:
            return

        if self.setting_service.verify_app_pin(entered_pin):
            self._is_authenticated = True
            self.accept()
        else:
            msg = QMessageBox()  # Khởi tạo không cha để tránh dính lỗi layout viền trên Mac
            self._apply_modern_msg_style(msg)

            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Lỗi bảo mật")
            msg.setText("Mã bảo vệ PIN không chính xác. Vui lòng kiểm tra lại!")
            msg.exec()

            self.ui.txt_pin.clear()
            self.ui.txt_pin.setFocus()

    def show_forgot_pin_notice(self):
        msg = QMessageBox()
        self._apply_modern_msg_style(msg)

        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Bảo mật hệ thống")
        msg.setText(
            "Vui lòng liên hệ Kỹ thuật viên / Đơn vị cung cấp phần mềm qua SĐT hoặc Zalo để được hỗ trợ mở khóa từ xa."
        )
        msg.exec()
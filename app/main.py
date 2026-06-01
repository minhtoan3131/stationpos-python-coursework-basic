import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from app.core.database.connection import DatabaseConnection
from app.modules.main_window.main_window import MainWindow


def main():
    # Khởi tạo Application
    app = QApplication(sys.argv)

    # Ép sử dụng style "Fusion" để giao diện đồng bộ, đẹp mắt trên cả Mac và Windows
    app.setStyle("Fusion")

    # Kiểm tra kết nối CSDL (Fail-Fast: Báo lỗi sớm nếu MySQL chưa bật)
    try:
        print("Đang kiểm tra kết nối Database...")
        conn = DatabaseConnection.get_connection()
        conn.close()
        print("Kết nối Database thành công!")
    except Exception as e:
        QMessageBox.critical(
            None,
            "Lỗi kết nối CSDL",
            f"Không thể kết nối đến Database. Vui lòng kiểm tra lại MySQL (XAMPP/Docker) của bạn.\n\nChi tiết lỗi: {str(e)}"
        )
        sys.exit(1)

    # Khởi chạy giao diện chính
    try:
        window = MainWindow()
        window.showMaximized()  # Hiển thị full màn hình ngay khi mở

        # Bắt đầu vòng lặp sự kiện chính của App
        sys.exit(app.exec())

    except Exception as e:
        traceback.print_exc()
        QMessageBox.critical(None, "Lỗi hệ thống", f"Không thể khởi động ứng dụng:\n{str(e)}")


if __name__ == "__main__":
    main()
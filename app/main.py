import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox

# Import Database Connection để test kết nối trước khi khởi động
from app.core.database.connection import DatabaseConnection

# Import MainWindow (Đảm bảo đường dẫn này khớp với thư mục của bạn)
from app.modules.main_window.main_window import MainWindow


def main():
    # 1. Khởi tạo Application
    app = QApplication(sys.argv)

    # Ép sử dụng style "Fusion" để giao diện đồng bộ, đẹp mắt trên cả Mac và Windows
    app.setStyle("Fusion")

    # 2. Kiểm tra kết nối CSDL (Fail-Fast: Báo lỗi sớm nếu MySQL chưa bật)
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

    # 3. Khởi chạy giao diện chính
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
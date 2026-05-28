import pytest
import mysql.connector


# Thiết lập kết nối tới DB Test một lần duy nhất cho toàn bộ session test
@pytest.fixture(scope="session")
def db_test_connection():
    connection = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password=os.getenv("DB_PASSWORD", ""),
        database="pos_vpp_test"
    )
    yield connection
    connection.close()


@pytest.fixture(autouse=True)
def clean_db(db_test_connection):
    """Xóa sạch toàn bộ các bảng trong CSDL Test trước MỖI bài test để đảm bảo tính cô lập."""
    cursor = db_test_connection.cursor()

    # 1. Tắt kiểm tra khóa ngoại (Foreign Key) để có thể Truncate thoải mái
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # 2. Xóa sạch dữ liệu tất cả các bảng

    # Nhóm Sổ cái và Nhật ký đóng băng Thuế mới (Xóa Detail trước Master vì ràng buộc khóa ngoại)
    cursor.execute("TRUNCATE TABLE tax_ledger_details;")
    cursor.execute("TRUNCATE TABLE tax_ledger;")

    # Nhóm Bán hàng (Sale)
    cursor.execute("TRUNCATE TABLE invoice_logs;")
    cursor.execute("TRUNCATE TABLE invoice_items;")
    cursor.execute("TRUNCATE TABLE invoices;")

    # Nhóm Nhập kho & Tồn kho (Inventory)
    cursor.execute("TRUNCATE TABLE stock_transactions;")
    cursor.execute("TRUNCATE TABLE purchase_order_items;")
    cursor.execute("TRUNCATE TABLE purchase_orders;")
    cursor.execute("TRUNCATE TABLE inventory;")

    # Nhóm Sản phẩm (Product) & Phụ trợ
    cursor.execute("TRUNCATE TABLE unit_conversions;")
    cursor.execute("TRUNCATE TABLE products;")
    cursor.execute("TRUNCATE TABLE categories;")
    cursor.execute("TRUNCATE TABLE suppliers;")
    cursor.execute("TRUNCATE TABLE units;")

    # Cấu hình chung hệ thống
    cursor.execute("TRUNCATE TABLE system_settings;")
    cursor.execute("TRUNCATE TABLE settings;")

    # 3. Bật lại kiểm tra khóa ngoại
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    db_test_connection.commit()
    cursor.close()
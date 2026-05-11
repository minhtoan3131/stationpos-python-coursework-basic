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
    """Xóa sạch và mồi dữ liệu khóa ngoại trước mỗi hàm test để đảm bảo tính độc lập."""
    cursor = db_test_connection.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    cursor.execute("TRUNCATE TABLE stock_transactions")
    cursor.execute("TRUNCATE TABLE inventory")
    cursor.execute("TRUNCATE TABLE unit_conversions")
    cursor.execute("TRUNCATE TABLE products")
    cursor.execute("TRUNCATE TABLE categories")
    cursor.execute("TRUNCATE TABLE suppliers")
    cursor.execute("TRUNCATE TABLE units")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Văn phòng phẩm')")
    cursor.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Thiên Long')")
    cursor.execute("INSERT INTO units (id, name) VALUES (1, 'Cái'), (2, 'Hộp')")

    db_test_connection.commit()
    cursor.close()
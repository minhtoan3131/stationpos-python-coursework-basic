import pytest
import mysql.connector


@pytest.fixture(autouse=True)
def seed_db(db_test_connection):
    """Mồi dữ liệu khóa ngoại trước mỗi hàm test để đảm bảo tính độc lập."""
    cursor = db_test_connection.cursor()

    cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Văn phòng phẩm')")
    cursor.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Thiên Long')")
    cursor.execute("INSERT INTO units (id, name) VALUES (1, 'Cái'), (2, 'Hộp')")

    db_test_connection.commit()
    cursor.close()
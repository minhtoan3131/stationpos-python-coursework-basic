import pytest


@pytest.fixture(autouse=True)
def seed_tax_system_settings(db_test_connection):
    """Tự động chèn các tham số quy mô ngầm vào DB Test trước mỗi bài test của riêng module tax"""
    cursor = db_test_connection.cursor()
    query = """
        INSERT INTO system_settings (setting_key, setting_value, description)
        VALUES 
            ('TAX_MID_SCALE_LIMIT', '3000000000', 'Mốc giới hạn doanh thu bắt buộc sổ sách kế toán'),
            ('TAX_LARGE_SCALE_LIMIT', '50000000000', 'Mốc giới hạn doanh thu quy mô lớn nhất')
        ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
    """
    try:
        cursor.execute(query)
        db_test_connection.commit()
    finally:
        cursor.close()
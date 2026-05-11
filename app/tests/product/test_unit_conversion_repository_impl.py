import pytest
from app.modules.product.repositories.impl.unit_conversion_repository_impl import UnitConversionRepositoryImpl
from app.modules.product.entities.unit_conversion import UnitConversion


# ==========================================
# 1. FIXTURES
# ==========================================

@pytest.fixture
def unit_conv_repo(db_test_connection):
    return UnitConversionRepositoryImpl(db_test_connection)


@pytest.fixture
def setup_dummy_product(db_test_connection):
    """
    Vì bảng unit_conversions yêu cầu khóa ngoại product_id,
    ta cần một fixture để tạo nhanh 1 sản phẩm giả dưới DB Test.
    Trả về product_id vừa tạo.
    """
    cursor = db_test_connection.cursor()
    # Chèn 1 sản phẩm giả (Giả định các category, supplier, unit đã được mồi từ clean_db)
    cursor.execute("""
        INSERT INTO products (sku, name, category_id, supplier_id, base_unit_id, cost_price, retail_price, wholesale_price)
        VALUES ('SKU-CONV-TEST', 'Sản phẩm Test Quy Đổi', 1, 1, 1, 1000, 2000, 1500)
    """)
    product_id = cursor.lastrowid
    db_test_connection.commit()
    cursor.close()

    return product_id


# ==========================================
# 2. TEST CASES
# ==========================================

def test_create_and_get_unit_conversion(unit_conv_repo, setup_dummy_product):
    # GIVEN
    product_id = setup_dummy_product
    conversion_to_create = UnitConversion(
        id=None,
        product_id=product_id,
        from_unit_id=1,  # VD: 1 là Cái
        to_unit_id=2,  # VD: 2 là Hộp
        ratio=12.0
    )

    # WHEN - CREATE
    new_id = unit_conv_repo.create_unit_conversion(conversion_to_create)

    # THEN
    assert new_id > 0

    # WHEN - GET
    db_conversion = unit_conv_repo.get_unit_conversion(product_id)

    # THEN - Kiểm tra mapping dữ liệu
    assert db_conversion is not None
    assert db_conversion.product_id == product_id
    assert db_conversion.from_unit_id == 1
    assert db_conversion.to_unit_id == 2
    # MySQL Decimal khi kéo lên Python sẽ là kiểu Decimal, nên ép về float để so sánh
    assert float(db_conversion.ratio) == 12.0


def test_update_unit_conversion(unit_conv_repo, setup_dummy_product):
    # GIVEN: Tạo sẵn 1 quy đổi tỷ lệ 12
    product_id = setup_dummy_product
    conversion = UnitConversion(
        id=None, product_id=product_id, from_unit_id=1, to_unit_id=2, ratio=12.0
    )
    unit_conv_repo.create_unit_conversion(conversion)

    # WHEN: Cập nhật tỷ lệ lên 24
    conversion.ratio = 24.0
    is_updated = unit_conv_repo.update_unit_conversion(conversion)

    # THEN
    assert is_updated is True

    # Xác minh dưới DB
    db_conversion = unit_conv_repo.get_unit_conversion(product_id)
    assert float(db_conversion.ratio) == 24.0


def test_get_non_existent_conversion(unit_conv_repo):
    # Khi truy vấn một product_id chưa từng có quy đổi
    # Phải đảm bảo repo xử lý êm đẹp và trả về None (không bị crash)
    result = unit_conv_repo.get_unit_conversion(999999)
    assert result is None
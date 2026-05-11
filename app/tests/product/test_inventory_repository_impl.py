import pytest
from app.modules.product.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl




@pytest.fixture
def inventory_repo(db_test_connection):
    return InventoryRepositoryImpl(db_test_connection)


@pytest.fixture
def setup_dummy_product(db_test_connection):
    """
    Tạo nhanh 1 sản phẩm giả dưới DB Test để lấy product_id làm khóa ngoại.
    (Giả định categories, suppliers, units đã được mồi bởi clean_db)
    """
    cursor = db_test_connection.cursor()
    cursor.execute("""
        INSERT INTO products (sku, name, category_id, supplier_id, base_unit_id, cost_price, retail_price, wholesale_price)
        VALUES ('SKU-INV-TEST', 'Sản phẩm Test Tồn Kho', 1, 1, 1, 1000, 2000, 1500)
    """)
    product_id = cursor.lastrowid
    db_test_connection.commit()
    cursor.close()

    return product_id


# ==========================================
# TEST CASES
# ==========================================

def test_get_inventory_quantity_has_data(inventory_repo, setup_dummy_product, db_test_connection):
    """Kịch bản 1: Sản phẩm đã có dòng dữ liệu trong bảng inventory"""

    product_id = setup_dummy_product

    # GIVEN: Can thiệp bằng SQL thuần để bơm dữ liệu vào bảng inventory
    cursor = db_test_connection.cursor()
    cursor.execute(
        "INSERT INTO inventory (product_id, quantity, updated_at) VALUES (%s, %s, NOW())",
        (product_id, 150)
    )
    db_test_connection.commit()
    cursor.close()

    # WHEN: Gọi hàm của Repository
    quantity = inventory_repo.get_inventory_quantity(product_id)

    # THEN: Phải đọc lên được số 150
    assert quantity == 150


def test_get_inventory_quantity_no_data(inventory_repo, setup_dummy_product):
    """Kịch bản 2: Sản phẩm tồn tại nhưng CHƯA phát sinh tồn kho"""

    # GIVEN: Chỉ tạo product, KHÔNG insert vào bảng inventory
    product_id = setup_dummy_product

    # WHEN
    quantity = inventory_repo.get_inventory_quantity(product_id)

    # THEN: Logic `if row else 0` phải hoạt động và trả về 0
    assert quantity == 0


def test_get_inventory_quantity_invalid_id(inventory_repo):
    """Kịch bản 3: Truy vấn một ID sản phẩm hoàn toàn không có thực"""

    # WHEN
    quantity = inventory_repo.get_inventory_quantity(999999)

    # THEN: Cũng phải trả về 0 một cách an toàn mà không bị crash
    assert quantity == 0
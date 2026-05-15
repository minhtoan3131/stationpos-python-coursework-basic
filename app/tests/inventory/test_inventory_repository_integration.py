import pytest
import mysql.connector
from app.modules.inventory.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl


# ==========================================
# FIXTURE KHỞI TẠO REPO & DATA MỒI DÀNH RIÊNG CHO INVENTORY
# ==========================================
@pytest.fixture
def inv_repo(db_test_connection):
    return InventoryRepositoryImpl(db_test_connection)


@pytest.fixture
def seed_inventory_data(db_test_connection):
    """Fixture này chỉ được chạy nếu bài test nào gọi tên nó"""
    cursor = db_test_connection.cursor()
    # Mồi ĐVT
    cursor.execute("INSERT INTO units (id, name) VALUES (10, 'Cây'), (11, 'Hộp')")
    # Mồi Sản phẩm
    cursor.execute(
        "INSERT INTO products (id, sku, name, base_unit_id, is_active) VALUES (100, 'SP01', 'Bút bi', 10, 1)")

    cursor.execute(
        "INSERT INTO unit_conversions (product_id, from_unit_id, to_unit_id, ratio) VALUES (100, 10, 11, 20)")

    # Mồi Tồn kho
    cursor.execute("INSERT INTO inventory (product_id, quantity, total_value) VALUES (100, 25, 125000)")

    db_test_connection.commit()
    cursor.close()


# ==========================================
# TEST CASES
# ==========================================
def test_get_inventory_list_data_joins_correctly(inv_repo, seed_inventory_data):
    """Kiểm chứng câu SELECT LEFT JOIN 4 bảng lấy đủ dữ liệu"""

    # ACT
    results = inv_repo.get_inventory_list_data(search_keyword="Bút")

    # ASSERT
    assert len(results) == 1
    row = results[0]
    # Kiểm tra xem JOIN bảng products và inventory có khớp không
    assert row['total_base_quantity'] == 25
    # Kiểm tra xem JOIN bảng units và unit_conversions có khớp không
    assert row['base_unit_name'] == 'Cây'
    assert row['conversion_unit_name'] == 'Hộp'
    assert row['conversion_ratio'] == 20


def test_create_purchase_order_fails_foreign_key_constraint(inv_repo):
    """Ràng buộc Khóa ngoại (Supplier MA)"""

    po_data = {'code': 'PO-001', 'supplier_id': 9999, 'total_amount': 50000, 'note': 'Test FK'}

    with pytest.raises(mysql.connector.Error) as exc_info:
        inv_repo.create_purchase_order(po_data)

    # mysql.connector ném ra lỗi liên quan đến FOREIGN KEY
    assert "foreign key constraint fails" in str(exc_info.value).lower()
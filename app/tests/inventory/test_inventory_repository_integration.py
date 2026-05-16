from decimal import Decimal

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


def test_get_inventory_status_for_sale(inv_repo, seed_inventory_data):
    """Đảm bảo lấy đúng tồn kho và tổng giá trị để SaleService kiểm tra trước khi bán"""
    status = inv_repo.get_inventory_status(100)

    assert status is not None
    assert status['quantity'] == 25
    # So sánh với chuỗi Decimal để tránh sai số thập phân
    assert Decimal(str(status['total_value'])) == Decimal('125000.0000')


def test_update_inventory_status_after_sale(inv_repo, seed_inventory_data, db_test_connection):
    """Đảm bảo lệnh UPDATE trừ kho và cập nhật giá vốn MAC ghi xuống DB thành công"""

    # ACT: Bán đi 5 cây, tổng giá trị kho còn lại 100k
    inv_repo.update_inventory_status(100, 20, Decimal('100000.0000'))
    db_test_connection.commit()

    # ASSERT: Query trực tiếp xuống DB để kiểm chứng
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT quantity, total_value FROM inventory WHERE product_id = 100")
    row = cursor.fetchone()

    assert row['quantity'] == 20
    assert Decimal(str(row['total_value'])) == Decimal('100000.0000')


def test_add_stock_transaction_for_sale(inv_repo, seed_inventory_data, db_test_connection):
    """Lệnh INSERT log lịch sử biến động kho (SALE) phải map đúng cột"""

    trans_data = {
        'product_id': 100,
        'qty': -5,
        'type': 'SALE',
        'ref_id': 888
    }

    # ACT
    inv_repo.add_stock_transaction(trans_data)
    db_test_connection.commit()

    # ASSERT
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM stock_transactions WHERE product_id = 100 AND type = 'SALE'")
    logs = cursor.fetchall()

    assert len(logs) == 1
    assert logs[0]['change_quantity'] == -5
    assert logs[0]['reference_id'] == 888
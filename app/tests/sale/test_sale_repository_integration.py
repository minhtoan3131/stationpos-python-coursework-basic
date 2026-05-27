import pytest
from decimal import Decimal
import mysql.connector
from app.modules.sale.repositories.impl.sale_repository_impl import SaleRepositoryImpl
from app.modules.inventory.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO


@pytest.fixture
def real_repos(db_test_connection):
    """Khởi tạo cặp đôi Repository chạy trực tiếp trên MySQL Test"""
    return SaleRepositoryImpl(db_test_connection), InventoryRepositoryImpl(db_test_connection)


def test_create_invoice_items_stores_snapshot_total_cogs(real_repos, db_test_connection):
    """Kiểm toán cú pháp SQL: Đảm bảo Bulk Insert ghi nhận chính xác cột total_cogs_amount gánh rác"""
    sale_repo, inv_repo = real_repos
    cursor = db_test_connection.cursor(dictionary=True)

    # 1. Thiết lập cấu trúc danh mục mồi chống lỗi khóa ngoại (Foreign Key)
    cursor.execute("INSERT INTO units (id, name) VALUES (10, 'Cái')")
    cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'VPP')")
    cursor.execute("INSERT INTO products (id, sku, name, category_id, base_unit_id) VALUES (100, 'SP01', 'Bút bi', 1, 10)")
    db_test_connection.commit()

    checkout_data = CheckoutDTO(
        code="HD-INTEGRATION-001", total_amount=Decimal('50000'), discount=Decimal('0'),
        final_amount=Decimal('50000'), payment_method='CASH', cash_received=Decimal('50000'), items=[]
    )

    items = [
        CartItemDTO(
            product_id=100, sku="SP01", name="Bút", unit_id=10, unit_name="Cái", quantity=5,
            price=Decimal('10000'), total=Decimal('50000'), cost_price=Decimal('4000'),
            total_cogs_amount=Decimal('20000.0005')  # Giả lập con số COGS chứa rác thập phân lẻ
        )
    ]

    # 2. ACT
    invoice_id = sale_repo.create_invoice(checkout_data)
    sale_repo.create_invoice_items(invoice_id, items)
    db_test_connection.commit()

    # 3. ASSERT: Kiểm chứng cột dữ liệu tài chính trong MySQL thật
    cursor.execute("SELECT total_cogs_amount, cost_price FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
    row = cursor.fetchone()

    assert row is not None
    # Hệ thống MySQL kiểu DECIMAL(15, 4) phải lưu vết nguyên vẹn snapshot giá vốn gánh rác
    assert row['total_cogs_amount'] == Decimal('20000.0005')


def test_link_stock_transactions_to_invoice_by_specific_ids(real_repos, db_test_connection):
    """Kiểm toán tích hợp: Hàm liên kết ID phải cập nhật chính xác reference_id, chống quét mù gây trùng lặp"""
    sale_repo, inv_repo = real_repos
    cursor = db_test_connection.cursor(dictionary=True)

    # 1. GIVEN: ĐÃ BỔ SUNG - Mồi dữ liệu danh mục cơ bản để không bị vi phạm ràng buộc Khóa ngoại (Foreign Key)
    cursor.execute("INSERT INTO units (id, name) VALUES (10, 'Cái')")
    cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'VPP')")
    cursor.execute("INSERT INTO products (id, sku, name, category_id, base_unit_id) VALUES (100, 'SP01', 'Bút bi', 1, 10)")
    db_test_connection.commit()

    # 2. Sinh 2 dòng log kho có reference_id ban đầu bằng NULL
    # (Dòng 1 của ta, Dòng 2 giả lập của thu ngân khác chạy song song)
    tx_id_1 = inv_repo.add_stock_transaction({'product_id': 100, 'qty': -5, 'type': 'SALE'})
    tx_id_2 = inv_repo.add_stock_transaction({'product_id': 100, 'qty': -10, 'type': 'SALE'})
    db_test_connection.commit()

    # Tạo sẵn 1 hóa đơn thật có mã code cụ thể
    checkout_data = CheckoutDTO(
        code="HD-LINK-999", total_amount=Decimal('10'), discount=Decimal('0'), final_amount=Decimal('10'),
        payment_method='CASH', cash_received=Decimal('10'), items=[]
    )
    invoice_id = sale_repo.create_invoice(checkout_data)
    db_test_connection.commit()

    # 3. ACT: Chỉ truyền duy nhất ID dòng 1 đi liên kết hóa đơn
    inv_repo.link_stock_transactions_to_invoice([tx_id_1], invoice_id)
    db_test_connection.commit()

    # 4. ASSERT: Chứng minh tính cô lập luồng dữ liệu (Thread-safe)
    cursor.execute("SELECT id, reference_id FROM stock_transactions WHERE id IN (%s, %s) ORDER BY id", (tx_id_1, tx_id_2))
    rows = cursor.fetchall()

    # Dòng 1 bắt buộc phải được map trúng đích khóa ngoại reference_id
    assert rows[0]['id'] == tx_id_1
    assert rows[0]['reference_id'] == invoice_id

    # Dòng 2 (của luồng khác chạy song song) tuyệt đối KHÔNG ĐƯỢC phép bị cập nhật oan, phải giữ nguyên trạng NULL!
    assert rows[1]['id'] == tx_id_2
    assert rows[1]['reference_id'] is None
import pytest
from decimal import Decimal
import mysql.connector  # Đã sửa từ pymysql sang mysql.connector theo đúng thư viện của dự án

from app.modules.sale.repositories.impl.sale_repository_impl import SaleRepositoryImpl
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO


@pytest.fixture
def real_sale_repo(db_test_connection):
    """Tạo Real Repository và bơm Connection thật của DB Test vào"""
    repo = SaleRepositoryImpl(db_test_connection)
    # Lớp BaseRepository của bạn khởi tạo cursor trong __init__,
    # nên ta khởi tạo lại repo với connection thật
    return repo


# ==========================================
# 1. TEST INSERT HÓA ĐƠN & CHI TIẾT (BULK INSERT)
# ==========================================
def test_create_invoice_and_items_sql_syntax(real_sale_repo, db_test_connection):
    """Đảm bảo câu lệnh INSERT và executemany không bị sai chính tả SQL"""

    # 1. ARRANGE: Tạo sẵn Đơn vị và Sản phẩm mồi để không bị lỗi Khóa Ngoại (Foreign Key)
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("INSERT INTO units (id, name) VALUES (10, 'Cái')")
    cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'VPP')")
    cursor.execute("""
        INSERT INTO products (id, sku, name, category_id, base_unit_id) 
        VALUES (100, 'SP01', 'Bút bi', 1, 10), (101, 'SP02', 'Thước kẻ', 1, 10)
    """)
    db_test_connection.commit()

    # Chuẩn bị DTO hóa đơn
    checkout_data = CheckoutDTO(
        code="HD-TEST-001", total_amount=Decimal('150000'), discount=Decimal('0'),
        final_amount=Decimal('150000'), payment_method='CASH', cash_received=Decimal('200000'),
        items=[]  # Trống tạm thời
    )

    items = [
        CartItemDTO(product_id=100, sku="SP01", name="Bút", unit_id=10, unit_name="Cái", quantity=5,
                    price=Decimal('10000'), total=Decimal('50000'),
                    cost_price=Decimal('4000')  # ĐÃ THÊM GIÁ VỐN
                    ),
        CartItemDTO(product_id=101, sku="SP02", name="Thước", unit_id=10, unit_name="Cái", quantity=5,
                    price=Decimal('20000'), total=Decimal('100000'),
                    cost_price=Decimal('8000')  # ĐÃ THÊM GIÁ VỐN
                    )
    ]

    # 2. ACT: Gọi hàm thật đâm xuống MySQL
    invoice_id = real_sale_repo.create_invoice(checkout_data)
    real_sale_repo.create_invoice_items(invoice_id, items)
    db_test_connection.commit()  # Chốt dữ liệu

    # 3. ASSERT: Query ngược lại từ DB lên để kiểm chứng
    # Kiểm tra Header (Invoices)
    cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    saved_invoice = cursor.fetchone()
    assert saved_invoice['code'] == "HD-TEST-001"
    assert saved_invoice['final_amount'] == Decimal('150000.00')

    # Kiểm tra Details (Invoice_items) xem executemany có ăn đủ 2 dòng không và có lưu giá vốn không
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s ORDER BY product_id", (invoice_id,))
    saved_items = cursor.fetchall()
    assert len(saved_items) == 2

    assert saved_items[0]['product_id'] == 100
    assert saved_items[0]['quantity'] == 5
    # MySQL kiểu DECIMAL(15,4) sẽ trả về chuỗi có 4 số 0 ở thập phân
    assert saved_items[0]['cost_price'] == Decimal('4000.0000')

    assert saved_items[1]['product_id'] == 101
    assert saved_items[1]['quantity'] == 5
    assert saved_items[1]['cost_price'] == Decimal('8000.0000')


# ==========================================
# 2. TEST BẢO VỆ KHÓA NGOẠI (FOREIGN KEY CONSTRAINTS)
# ==========================================
def test_create_invoice_items_fails_foreign_key(real_sale_repo):
    """Nếu insert chi tiết cho một Hóa đơn MA hoặc Sản phẩm MA -> DB phải chặn"""

    # Chuẩn bị món hàng có product_id = 9999 (Sản phẩm ma, không tồn tại trong bảng products)
    items = [
        CartItemDTO(product_id=9999, sku="MA", name="MA", unit_id=10, unit_name="Cái", quantity=1,
                    price=Decimal('1'), total=Decimal('1'),
                    cost_price=Decimal('1')
                    )
    ]

    # Cố tình nhét vào một Hóa đơn cũng MA nốt (invoice_id = 9999)
    # Bắt lỗi theo chuẩn của thư viện mysql-connector-python
    with pytest.raises(mysql.connector.Error) as exc_info:
        real_sale_repo.create_invoice_items(invoice_id=9999, items=items)

    # Phải bắt đúng lỗi vi phạm khóa ngoại
    assert "foreign key constraint fails" in str(exc_info.value).lower()
import pytest
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl


# ==========================================
# SETUP FAKE REPOSITORIES & UOW (STATE-BASED)
# ==========================================

class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10},
            200: {'id': 200, 'name': 'Sổ tay', 'base_unit_id': 20}
        }

    def get_product_by_id(self, product_id):
        return type('Product', (object,), self.products[product_id]) if product_id in self.products else None


class FakeInventoryRepo:
    def __init__(self):
        # Kho 1: Bút bi có 50 cái. Tổng giá trị 200k => Giá vốn MAC = 4k/cái
        # Kho 2: Sổ tay có 100 cuốn. Tổng giá trị 500k => Giá vốn MAC = 5k/cuốn
        self.inventory = {
            100: {'quantity': 50, 'total_value': Decimal('200000')},
            200: {'quantity': 100, 'total_value': Decimal('500000')}
        }
        self.stock_transactions = []

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {'quantity': 0, 'total_value': Decimal('0')})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data):
        self.stock_transactions.append(trans_data)


class FakeSaleRepo:
    def __init__(self):
        self.invoices = []
        self.invoice_items = []
        self.invoice_logs = []
        self.next_invoice_id = 1

    def create_invoice(self, checkout_data):
        # Trích xuất dữ liệu sang dict để dễ verify (giống như lưu vào DB)
        invoice = {
            'id': self.next_invoice_id,
            'code': checkout_data.code,
            'total_amount': checkout_data.total_amount,
            'final_amount': checkout_data.final_amount,
            'payment_method': checkout_data.payment_method
        }
        self.invoices.append(invoice)
        self.next_invoice_id += 1
        return invoice['id']

    def create_invoice_items(self, invoice_id, items):
        for item in items:
            self.invoice_items.append({'invoice_id': invoice_id, 'item': item})

    def add_invoice_log(self, invoice_id, action, note):
        self.invoice_logs.append({'invoice_id': invoice_id, 'action': action, 'note': note})


# FAKE CONNECTION & CURSOR
class FakeCursor:
    def __init__(self, fake_inv_repo):
        self.result = None
        self.fake_inv_repo = fake_inv_repo

    def execute(self, sql, params):
        # 1. Giả lập kết quả cho câu lệnh SELECT ratio quy đổi
        if "unit_conversions" in sql:
            p_id, u_id = params
            # Giả lập: Nếu mua Sổ tay (ID 200) bằng ĐVT Hộp (ID 21) => Trả về ratio = 10 (1 Hộp = 10 cuốn)
            if p_id == 200 and u_id == 21:
                self.result = {'ratio': 10}
            else:
                self.result = None

        # 2. Giả lập kết quả cho câu lệnh SELECT quantity, total_value từ inventory
        elif "inventory" in sql:
            p_id = params[0]
            inv = self.fake_inv_repo.get_inventory_status(p_id)
            if inv:
                self.result = {'quantity': inv['quantity'], 'total_value': inv['total_value']}
            else:
                self.result = None

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, fake_inv_repo):
        self.fake_inv_repo = fake_inv_repo

    def cursor(self, dictionary=False):
        return FakeCursor(self.fake_inv_repo)


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.sale_repo = FakeSaleRepo()
        self.connection = FakeConnection(self.inventory_repo)

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def uow():
    """Tạo ra UOW để bài test có thể truy cập trực tiếp vào Fake DB nhằm Assert"""
    return FakeUnitOfWork()


@pytest.fixture
def sale_service(uow):
    return SaleServiceImpl(lambda: uow)


# ==========================================
# BÀI TEST CHÍNH: KIỂM CHỨNG TOÀN BỘ POST-CONDITIONS
# ==========================================

def test_checkout_happy_path_state_changes(sale_service, uow):

    # ==========================================
    # GIVEN: Khách mua 2 mặt hàng (1 bán lẻ, 1 bán sỉ)
    # ==========================================
    # Món 1 (Lẻ): Mua 5 cái Bút bi (Giá bán 10k/cái)
    item_base = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi",
        unit_id=10, unit_name="Cái", quantity=5,
        price=Decimal('10000'), total=Decimal('50000')
    )

    # Món 2 (Sỉ): Mua 2 Hộp Sổ tay (1 Hộp = 10 cuốn, Giá bán 60k/hộp)
    item_conv = CartItemDTO(
        product_id=200, sku="SP02", name="Sổ tay",
        unit_id=21, unit_name="Hộp", quantity=2,
        price=Decimal('60000'), total=Decimal('120000')
    )

    dto = CheckoutDTO(
        code="", total_amount=Decimal('170000'),
        discount=Decimal('0'), final_amount=Decimal('170000'),
        payment_method='CASH', cash_received=Decimal('200000'),  # Khách đưa 200k
        items=[item_base, item_conv]
    )

    # ==========================================
    # WHEN: Thực thi luồng thanh toán duy nhất
    # ==========================================
    saved_invoice_code = sale_service.process_checkout(dto)

    # ==========================================
    # THEN: Kiểm chứng Trạng thái hệ thống để lại
    # ==========================================
    db_sale = uow.sale_repo
    db_inv = uow.inventory_repo

    # --- TC_Post_01: Kiểm tra bảng Invoices (Header) ---
    assert len(db_sale.invoices) == 1
    invoice = db_sale.invoices[0]
    assert invoice['total_amount'] == Decimal('170000')
    assert invoice['payment_method'] == 'CASH'
    assert invoice['code'] == saved_invoice_code  # Mã HĐ phải được gán vào DTO và trả về

    # --- TC_Post_02: Kiểm tra bảng Invoice_Items (Details) ---
    assert len(db_sale.invoice_items) == 2
    assert db_sale.invoice_items[0]['item'].product_id == 100
    assert db_sale.invoice_items[1]['item'].product_id == 200

    # --- TC_Post_03: Kiểm tra trừ kho & Quy đổi ---
    # Bút bi (Lẻ): Tồn kho cũ 50, bán 5 -> Còn 45
    assert db_inv.inventory[100]['quantity'] == 45
    # Sổ tay (Sỉ): Tồn kho cũ 100, bán 2 Hộp (Ratio 10) -> Bán 20 cuốn -> Còn 80
    assert db_inv.inventory[200]['quantity'] == 80

    # --- TC_Post_04: Cập nhật giá trị tồn kho (MAC) ---
    # Bút bi: MAC là 4k/cái -> 45 cái * 4000 = 180,000
    assert db_inv.inventory[100]['total_value'] == Decimal('180000')
    # Sổ tay: MAC là 5k/cuốn -> 80 cuốn * 5000 = 400,000
    assert db_inv.inventory[200]['total_value'] == Decimal('400000')

    # --- TC_Post_05: Dấu vết Audit Trail ---
    # Kiểm tra log hóa đơn
    assert len(db_sale.invoice_logs) == 1
    assert db_sale.invoice_logs[0]['action'] == 'CREATE'

    # Kiểm tra transaction kho
    assert len(db_inv.stock_transactions) == 2
    # Bút bi phải ghi nhận biến động là -5
    assert db_inv.stock_transactions[0]['product_id'] == 100
    assert db_inv.stock_transactions[0]['qty'] == -5
    assert db_inv.stock_transactions[0]['type'] == 'SALE'

    # Sổ tay phải ghi nhận biến động CƠ BẢN là -20 (chứ không phải -2 hộp)
    assert db_inv.stock_transactions[1]['product_id'] == 200
    assert db_inv.stock_transactions[1]['qty'] == -20
    assert db_inv.stock_transactions[1]['type'] == 'SALE'
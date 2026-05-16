import pytest
import copy
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl


# ==========================================
# SETUP FAKE REPOSITORIES & UOW (CÓ CHỨC NĂNG ROLLBACK)
# ==========================================

class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10}
        }

    def get_product_by_id(self, product_id):
        return type('Product', (object,), self.products[product_id]) if product_id in self.products else None


class FakeInventoryRepo:
    def __init__(self):
        # Trạng thái ban đầu: Đang có 50 cây bút bi, tổng giá trị 200k
        self.inventory = {100: {'quantity': 50, 'total_value': Decimal('200000')}}
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
        invoice = {
            'id': self.next_invoice_id,
            'code': checkout_data.code,
            'total_amount': checkout_data.total_amount
        }
        self.invoices.append(invoice)
        self.next_invoice_id += 1
        return invoice['id']

    def create_invoice_items(self, invoice_id, items):
        for item in items:
            self.invoice_items.append({'invoice_id': invoice_id, 'item': item})

    def add_invoice_log(self, invoice_id, action, note):
        self.invoice_logs.append({'invoice_id': invoice_id, 'action': action, 'note': note})


# THIẾT KẾ FAKE CONNECTION & CURSOR
class FakeCursor:
    def __init__(self, fake_inv_repo):
        self.result = None
        self.fake_inv_repo = fake_inv_repo

    def execute(self, sql, params):
        if "unit_conversions" in sql:
            self.result = None  # Bài test này chỉ bán hàng bằng ĐVT cơ bản, không cần quy đổi
        elif "inventory" in sql:
            p_id = params[0]
            inv = self.fake_inv_repo.get_inventory_status(p_id)
            if inv:
                self.result = {'quantity': inv['quantity'], 'total_value': inv['total_value']}

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, fake_inv_repo):
        self.fake_inv_repo = fake_inv_repo

    def cursor(self, dictionary=False):
        return FakeCursor(self.fake_inv_repo)


# ==========================================
# CƠ CHẾ ROLLBACK (SNAPSHOT TRÊN RAM)
# ==========================================
class FakeUnitOfWork:
    def __init__(self, override_sale_repo=None):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        # Cho phép chèn Repo "Đột biến" vào để giả lập lỗi
        self.sale_repo = override_sale_repo or FakeSaleRepo()
        self.connection = FakeConnection(self.inventory_repo)

        # Biến chứa ảnh chụp trạng thái
        self._inv_snapshot = None
        self._sale_snapshot = None

    def __enter__(self):
        # SNAPSHOT: Chụp ảnh toàn bộ dữ liệu của Inventory và Sale trước giao dịch
        self._inv_snapshot = copy.deepcopy(self.inventory_repo.__dict__)
        self._sale_snapshot = copy.deepcopy(self.sale_repo.__dict__)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nếu có Exception bay ra (exc_type != None) -> ROLLBACK TOÀN BỘ
        if exc_type is not None:
            self.inventory_repo.__dict__ = self._inv_snapshot
            self.sale_repo.__dict__ = self._sale_snapshot


# ==========================================
# FIXTURES TẠO DỮ LIỆU
# ==========================================
@pytest.fixture
def valid_checkout_dto():
    item = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi",
        unit_id=10, unit_name="Cái", quantity=5,  # Mua 5 cái
        price=Decimal('10000'), total=Decimal('50000'),
        cost_price=Decimal('4000')
    )
    return CheckoutDTO(
        code="", total_amount=Decimal('50000'), discount=Decimal('0'),
        final_amount=Decimal('50000'), payment_method='CASH',
        cash_received=Decimal('50000'), items=[item]
    )


# ==========================================
# TEST CASES (INVARIANTS)
# ==========================================

def test_transaction_rollback_when_db_fails(valid_checkout_dto):
    """Tính toàn vẹn giao dịch - Rollback khi gặp sự cố giữa chừng"""

    # TẠO REPO ĐỘT BIẾN (Giả lập lỗi ở bước cuối cùng)
    class BuggySaleRepo(FakeSaleRepo):
        def add_invoice_log(self, invoice_id, action, note):
            # Hàm này được SaleServiceImpl gọi cuối cùng. Ta ném lỗi ở đây
            raise ConnectionError("Mất kết nối Database khi đang ghi log!")

    buggy_repo = BuggySaleRepo()
    uow_factory = lambda: FakeUnitOfWork(override_sale_repo=buggy_repo)
    service = SaleServiceImpl(uow_factory)

    # ACT: Thực hiện thanh toán
    with pytest.raises(Exception) as exc_info:
        service.process_checkout(valid_checkout_dto)

    # Đảm bảo lỗi đứt mạng đã bị ném ra
    assert "Mất kết nối Database" in str(exc_info.value)

    # ASSERT: KIỂM CHỨNG BẤT BIẾN (ROLLBACK THÀNH CÔNG)
    # Lấy repo thật từ UOW ra để kiểm tra
    inv_repo = service.uow_factory().inventory_repo

    # Tồn kho phải được trả về nguyên trạng 50, không bị trừ đi 5
    assert inv_repo.inventory[100]['quantity'] == 50
    # Giá trị kho giữ nguyên 200k
    assert inv_repo.inventory[100]['total_value'] == Decimal('200000')

    # Hóa đơn phải bị xóa sạch (Rollback), không có hóa đơn rác
    assert len(buggy_repo.invoices) == 0
    assert len(buggy_repo.invoice_items) == 0


def test_mathematical_limits_prevent_negative_inventory(valid_checkout_dto):
    """Cấm xuất âm và đảm bảo không có rác dữ liệu sinh ra"""

    uow_factory = lambda: FakeUnitOfWork()
    service = SaleServiceImpl(uow_factory)

    # GIVEN: Khách mua 100 cây bút (Trong khi kho chỉ có 50)
    valid_checkout_dto.items[0].quantity = 100

    # WHEN
    with pytest.raises(Exception) as exc_info:
        service.process_checkout(valid_checkout_dto)

    # Đảm bảo Service đã chặn lại bằng logic Validate
    assert "không đủ tồn kho" in str(exc_info.value)

    # THEN: Kiểm chứng tính bất biến (Trạng thái dữ liệu nguyên vẹn)
    inv_repo = service.uow_factory().inventory_repo
    sale_repo = service.uow_factory().sale_repo

    # Kho không bị trừ âm (giữ nguyên 50)
    assert inv_repo.inventory[100]['quantity'] == 50
    # Tuyệt đối không có Hóa đơn hay Log nào được sinh ra
    assert len(sale_repo.invoices) == 0
    assert len(inv_repo.stock_transactions) == 0
import pytest
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl


# ==========================================
# SETUP FAKE REPOSITORIES CHO HAPPY PATH
# ==========================================
class FakeProductRepo:
    def __init__(self):
        # Sản phẩm ID 100: Bút bi (ĐVT cơ bản, không quy đổi)
        self.products = {
            100: {'id': 100, 'conversion_unit_id': None, 'conversion_ratio': None, 'cost_price': Decimal('4800.0000')}
        }

    def get_product_detail_for_import(self, product_id):
        return self.products.get(product_id)

    def update_cost_price(self, product_id, new_mac):
        self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        # TỒN KHO HIỆN TẠI: 50 cây, tổng giá trị 240.000 (MAC hiện tại = 4.800đ)
        self.inventory = {
            100: {'quantity': 50, 'total_value': Decimal('240000.0000')}
        }
        self.stock_transactions = []

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id)

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data):
        self.stock_transactions.append(trans_data)


class FakePOHistoryRepo:
    def __init__(self):
        # PHIẾU CẦN HỦY (ID=1): Đang ở trạng thái COMPLETED
        self.po_master_table = {
            1: {'id': 1, 'status': 'COMPLETED', 'cancel_reason': None}
        }
        # CHI TIẾT PHIẾU: Lúc nhập đã nhập 20 cây, giá 6.000đ/cây -> Tổng = 120.000đ
        self.po_items_table = {
            1: [{'product_id': 100, 'sku': 'SP01', 'quantity': 20, 'unit_id': 1, 'total_price': Decimal('120000.0000')}]
        }

    def get_purchase_order_by_id(self, po_id):
        return self.po_master_table.get(po_id)

    def get_purchase_order_items(self, po_id):
        return self.po_items_table.get(po_id, [])

    def update_purchase_order_status(self, po_id, new_status, cancel_reason):
        self.po_master_table[po_id]['status'] = new_status
        self.po_master_table[po_id]['cancel_reason'] = cancel_reason


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.po_history_repo = FakePOHistoryRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURE (BƠM SERVICE VÀ UOW VÀO TEST)
# ==========================================
@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def po_service(uow):
    return PurchaseOrderHistoryServiceImpl(lambda: uow)


# ==========================================
# TEST CASE CHÍNH: KIỂM CHỨNG TRẠNG THÁI (POST-CONDITIONS)
# ==========================================
def test_cancel_purchase_order_happy_path_state_changes(po_service, uow):
    """Kiểm tra toàn bộ hệ quả sau khi hủy phiếu thành công (Trừ kho, trừ tiền, ghi log)"""

    # 1. WHEN: Thực hiện hành động hủy phiếu ID=1 với lý do "Phát hiện hàng lỗi"
    po_service.cancel_purchase_order(po_id=1, cancel_reason="Phát hiện hàng lỗi")

    # 2. THEN: Trích xuất các Fake Repositories để soi "dấu vết"
    db_po = uow.po_history_repo
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # --- TC_Post_01: Cập nhật trạng thái phiếu ---
    po_master = db_po.po_master_table[1]
    assert po_master['status'] == 'CANCELLED'
    assert po_master['cancel_reason'] == "Phát hiện hàng lỗi"

    # --- TC_Post_02: Khấu trừ tồn kho & Tính lại MAC lùi ---
    # Tồn kho cũ: 50. Số lượng cần trừ: 20 -> Tồn kho mới phải là 30
    assert db_inv.inventory[100]['quantity'] == 30

    # Tổng giá trị cũ: 240.000. Giá trị lô bị hủy: 120.000 -> Giá trị mới phải là 120.000
    assert db_inv.inventory[100]['total_value'] == Decimal('120000.0000')

    # Giá vốn MAC mới = 120.000 / 30 = 4.000
    assert db_prod.products[100]['cost_price'] == Decimal('4000.0000')

    # --- TC_Post_03: Ghi nhận lịch sử giao dịch (Audit Trail) ---
    assert len(db_inv.stock_transactions) == 1
    log = db_inv.stock_transactions[0]

    assert log['product_id'] == 100
    assert log['qty'] == -20  # Phải mang dấu âm
    assert log['type'] == 'CANCEL'  # Loại giao dịch phải là CANCEL
    assert log['ref_id'] == 1  # Tham chiếu đúng ID phiếu nhập
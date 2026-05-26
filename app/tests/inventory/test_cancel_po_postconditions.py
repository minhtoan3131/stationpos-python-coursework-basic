import pytest
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl


class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'conversion_unit_id': None, 'conversion_ratio': None, 'cost_price': Decimal('4800.0000')}
        }
    def get_product_detail_for_import(self, product_id): return self.products.get(product_id)
    def update_cost_price(self, product_id, new_mac): self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        # Tồn kho: 50 cây, tổng tiền 240k (MAC hiện hành = 4.800đ)
        self.inventory = {100: {'quantity': 50, 'total_value': Decimal('240000.0000')}}
        self.stock_transactions = []

    def get_inventory_status(self, product_id): return self.inventory.get(product_id)
    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}
    def add_stock_transaction(self, trans_data): self.stock_transactions.append(trans_data)


class FakePOHistoryRepo:
    def __init__(self):
        self.po_master_table = {1: {'id': 1, 'code': 'PO-123', 'status': 'COMPLETED', 'cancel_reason': None, 'created_at': '2023-10-01 12:00:00'}}
        # Phiếu nhập 20 cây x giá 6k = 120k tổng tiền nhập
        self.po_items_table = {
            1: [{'product_id': 100, 'sku': 'SP01', 'quantity': 20, 'unit_id': 1, 'total_price': Decimal('120000.0000')}]
        }

    def get_purchase_order_by_id(self, po_id): return self.po_master_table.get(po_id)
    def get_purchase_order_items(self, po_id): return self.po_items_table.get(po_id, [])
    def update_purchase_order_status(self, po_id, new_status, cancel_reason):
        self.po_master_table[po_id]['status'] = new_status
        self.po_master_table[po_id]['cancel_reason'] = cancel_reason
    def has_subsequent_delivery_transactions(self, product_id, po_created_at): return False


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.po_history_repo = FakePOHistoryRepo()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def uow(): return FakeUnitOfWork()


@pytest.fixture
def po_service(uow): return PurchaseOrderHistoryServiceImpl(lambda: uow)


def test_cancel_purchase_order_happy_path_state_changes(po_service, uow):
    """TC_Post_01 -> 03: Đảm bảo rút lùi chính xác tiền hàng và ghi log phân lớp minh bạch"""
    # ACT: Tiến hành hủy phiếu nhập
    po_service.cancel_purchase_order(po_id=1, cancel_reason="Sai đơn giá")

    db_po = uow.po_history_repo
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # --- TC_Post_01: Cập nhật Master sang CANCELLED ---
    assert db_po.po_master_table[1]['status'] == 'CANCELLED'
    assert db_po.po_master_table[1]['cancel_reason'] == "Sai đơn giá"

    # --- TC_Post_02: Khấu trừ số dư kho và tính lại MAC lùi lịch sử ---
    assert db_inv.inventory[100]['quantity'] == 30 # 50 cũ - 20 lùi = 30
    assert db_inv.inventory[100]['total_value'] == Decimal('120000.0000') # 240k cũ - 120k lùi = 120k
    assert db_prod.products[100]['cost_price'] == Decimal('4000.0000') # MAC mới: 120k / 30 = 4.000đ

    # --- TC_Post_03: Lưu vết Audit Trail chuẩn Schema CSDL ---
    assert len(db_inv.stock_transactions) == 1
    log = db_inv.stock_transactions[0]
    assert log['product_id'] == 100
    assert log['qty'] == -20 # Mang dấu âm thể hiện giảm lùi lịch sử
    assert log['type'] == 'CANCEL'
    assert log['ref_id'] == 1
    assert log['variance_amount'] == Decimal('0.0000')
    assert "Hủy phiếu nhập hệ thống" in log['note']
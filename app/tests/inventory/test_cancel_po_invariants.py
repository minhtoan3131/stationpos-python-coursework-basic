import pytest
import copy
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl


# ==========================================
# SETUP FAKE REPOSITORIES & FAKE TRANSACTION
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'conversion_unit_id': None, 'conversion_ratio': None, 'cost_price': Decimal('5000.0000')}
        }

    def get_product_detail_for_import(self, product_id): return self.products.get(product_id)

    def update_cost_price(self, product_id, new_mac): self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {
            100: {'quantity': 50, 'total_value': Decimal('250000.0000')}
        }
        self.stock_transactions = []

    def get_inventory_status(self, product_id): return self.inventory.get(product_id)

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data): self.stock_transactions.append(trans_data)


class FakePOHistoryRepo:
    def __init__(self):
        self.po_master_table = {1: {'id': 1, 'code': 'PO-001', 'status': 'COMPLETED', 'cancel_reason': None,
                                    'created_at': '2023-10-01 10:00:00'}}
        self.po_items_table = {
            1: [{'product_id': 100, 'sku': 'SP01', 'quantity': 50, 'unit_id': 1, 'total_price': Decimal('250000.0000')}]
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
        self._snapshot = None

    def __enter__(self):
        self._snapshot = {
            'products': copy.deepcopy(self.product_repo.products),
            'inventory': copy.deepcopy(self.inventory_repo.inventory),
            'transactions': copy.deepcopy(self.inventory_repo.stock_transactions),
            'po_master': copy.deepcopy(self.po_history_repo.po_master_table)
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.product_repo.products = self._snapshot['products']
            self.inventory_repo.inventory = self._snapshot['inventory']
            self.inventory_repo.stock_transactions = self._snapshot['transactions']
            self.po_history_repo.po_master_table = self._snapshot['po_master']


@pytest.fixture
def uow(): return FakeUnitOfWork()


@pytest.fixture
def po_service(uow): return PurchaseOrderHistoryServiceImpl(lambda: uow)


# ==========================================
# TEST CASES
# ==========================================
def test_cancel_po_transaction_rollback_on_unexpected_error(po_service, uow):
    """TC_Inv_01: Đảm bảo tính ACID - Hủy dở gặp lỗi hệ thống phải hoàn tác sạch 100% các bảng"""

    def mock_db_crash(*args, **kwargs):
        raise RuntimeError("Đứt kết nối tới cơ sở dữ liệu đột ngột!")

    uow.po_history_repo.update_purchase_order_status = mock_db_crash

    with pytest.raises(Exception, match="Đứt kết nối tới cơ sở dữ liệu đột ngột"):
        po_service.cancel_purchase_order(1, "Hủy do nhập sai")

    db_inv = uow.inventory_repo
    db_po = uow.po_history_repo

    assert db_inv.inventory[100]['quantity'] == 50
    assert db_po.po_master_table[1]['status'] == 'COMPLETED'
    assert len(db_inv.stock_transactions) == 0


def test_cancel_po_forces_absolute_zero_and_logs_variance_clearance(po_service, uow):
    """
    TC_Inv_02: Chốt chặn Minh bạch khi kho cạn sạch (new_qty == 0).
    Kiểm chứng: Ép giá trị tiền về 0 và hạch toán dòng ADJUST_VARIANCE mang số tiền rác.
    """
    # GIVEN: Số lượng 50 cây ứng với tiền nhập là 250k, nhưng kho đọng sai số float lịch sử thành 250.000,0001đ
    uow.inventory_repo.inventory[100]['total_value'] = Decimal('250000.0001')

    # WHEN: Thực thi hủy trọn vẹn lô hàng 50 cây
    po_service.cancel_purchase_order(1, "Hủy sạch kho")

    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # THEN: 1. Số lượng vật lý và tài chính bắt buộc ép chết về 0 tuyệt đối
    assert db_inv.inventory[100]['quantity'] == 0
    assert db_inv.inventory[100]['total_value'] == Decimal('0')
    assert db_prod.products[100]['cost_price'] == Decimal('0')

    # 2. Hệ thống phải ghi nhận 2 giao dịch: Log dọn rác ADJUST_VARIANCE và log CANCEL hàng vật lý
    assert len(db_inv.stock_transactions) == 2

    # Giao dịch hạch toán triệt tiêu rác tiền lẻ
    variance_log = db_inv.stock_transactions[0]
    assert variance_log['type'] == 'ADJUST_VARIANCE'
    assert variance_log['qty'] == 0  # Không biến động lượng vật lý
    assert variance_log['variance_amount'] == Decimal('0.0001')  # Truy tìm ra đúng lượng rác dư thừa
    assert "Điều chỉnh dọn rác giá trị tồn đọng khi kho trống" in variance_log['note']
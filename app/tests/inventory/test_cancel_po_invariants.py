import pytest
import copy
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl


# ==========================================
# 1. SETUP FAKE REPOSITORIES & FAKE TRANSACTION
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
        self.po_master_table = {1: {'id': 1, 'status': 'COMPLETED', 'cancel_reason': None}}
        self.po_items_table = {
            1: [{'product_id': 100, 'sku': 'SP01', 'quantity': 50, 'unit_id': 1, 'total_price': Decimal('250000.0000')}]
        }

    def get_purchase_order_by_id(self, po_id): return self.po_master_table.get(po_id)

    def get_purchase_order_items(self, po_id): return self.po_items_table.get(po_id, [])

    def update_purchase_order_status(self, po_id, new_status, cancel_reason):
        self.po_master_table[po_id]['status'] = new_status
        self.po_master_table[po_id]['cancel_reason'] = cancel_reason


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.po_history_repo = FakePOHistoryRepo()
        self._snapshot = None

    def __enter__(self):
        # 1. BẮT ĐẦU TRANSACTION: Chụp ảnh toàn bộ trạng thái dữ liệu hiện tại
        self._snapshot = {
            'products': copy.deepcopy(self.product_repo.products),
            'inventory': copy.deepcopy(self.inventory_repo.inventory),
            'transactions': copy.deepcopy(self.inventory_repo.stock_transactions),
            'po_master': copy.deepcopy(self.po_history_repo.po_master_table)
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 2. KẾT THÚC TRANSACTION: Nếu có bất kỳ lỗi nào văng ra (exc_type is not None)
        if exc_type is not None:
            # ROLLBACK: Phục hồi toàn bộ con trỏ dữ liệu về bản sao lúc mới vào
            self.product_repo.products = self._snapshot['products']
            self.inventory_repo.inventory = self._snapshot['inventory']
            self.inventory_repo.stock_transactions = self._snapshot['transactions']
            self.po_history_repo.po_master_table = self._snapshot['po_master']


# ==========================================
# 2. FIXTURE BƠM DỮ LIỆU
# ==========================================
@pytest.fixture
def uow(): return FakeUnitOfWork()


@pytest.fixture
def po_service(uow): return PurchaseOrderHistoryServiceImpl(lambda: uow)


# ==========================================
# 3. TEST CASES CHO BẤT BIẾN (INVARIANTS)
# ==========================================

def test_cancel_po_transaction_rollback_on_unexpected_error(po_service, uow):
    """TC_Inv_01: Mô phỏng đứt cáp mạng giữa chừng, đảm bảo Dữ liệu được Rollback 100%"""

    # 1. GIVEN: Trạng thái ban đầu hợp lệ.
    # Nhưng ta "cài cắm" một quả bom vào hàm cuối cùng (update_purchase_order_status)
    def mock_db_crash(*args, **kwargs):
        raise RuntimeError("Đứt kết nối tới cơ sở dữ liệu đột ngột!")

    uow.po_history_repo.update_purchase_order_status = mock_db_crash

    # 2. WHEN: Thực hiện hủy phiếu
    with pytest.raises(Exception, match="Đứt kết nối tới cơ sở dữ liệu đột ngột"):
        po_service.cancel_purchase_order(1, "Hủy do nhập sai")

    # 3. THEN: Kiểm chứng tính Bất biến.
    # Mặc dù các hàm trừ kho, tính MAC đã chạy qua trong Service, nhưng UOW đã tóm được lỗi và Rollback.
    db_inv = uow.inventory_repo
    db_po = uow.po_history_repo

    # Tồn kho PHẢI CÒN NGUYÊN 50 cây, KHÔNG BỊ TRỪ
    assert db_inv.inventory[100]['quantity'] == 50
    # Phiếu nhập PHẢI CÒN NGUYÊN trạng thái COMPLETED
    assert db_po.po_master_table[1]['status'] == 'COMPLETED'
    # Không có log giao dịch nào được ghi nhầm
    assert len(db_inv.stock_transactions) == 0


def test_cancel_po_forces_absolute_zero_when_inventory_depleted(po_service, uow):
    """TC_Inv_02: Trừ sạch kho về 0 -> Ép tổng tiền và MAC về chuẩn 0 VNĐ"""

    # 1. GIVEN: Thiết lập sai số thập phân (Giả lập lỗi Float)
    # Lô hàng nhập 50 cây giá 250.000đ.
    # Nhưng trong kho hiện tại (do một lỗi làm tròn nào đó trong lịch sử), tổng giá trị đang là 250.000.0001đ
    uow.inventory_repo.inventory[100]['total_value'] = Decimal('250000.0001')

    # 2. WHEN: Hủy chính lô hàng 50 cây đó (Cạn sạch kho)
    po_service.cancel_purchase_order(1, "Hủy sạch kho")

    # 3. THEN: Kiểm chứng chốt chặn 0
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # Số lượng kho vè 0
    assert db_inv.inventory[100]['quantity'] == 0

    # Bất biến: Tổng tiền kho và Giá vốn MAC PHẢI BỊ ÉP VỀ 0 TUYỆT ĐỐI (Triệt tiêu sai số 0.0001)
    assert db_inv.inventory[100]['total_value'] == Decimal('0')
    assert db_prod.products[100]['cost_price'] == Decimal('0')
import pytest
import copy
from decimal import Decimal
from datetime import datetime
from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl


# ==========================================
# SETUP STATE SNAPSHOT FOR INVARIANTS
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {100: {'cost_price': Decimal('4000.0000')}}

    def update_cost_price(self, product_id, new_mac):
        self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {100: {'quantity': 0, 'total_value': Decimal('0.0000')}}
        self.stock_transactions = []

    def get_inventory_status(self, product_id): return self.inventory.get(product_id)

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data): self.stock_transactions.append(trans_data)


class FakeSaleRepo:
    def add_invoice_log(self, invoice_id, action, note): pass


class FakeInvoiceHistoryRepository:
    def __init__(self):
        self.meta = {'id': 1, 'code': 'HD-001', 'status': 'COMPLETED', 'created_at': datetime.now()}

    def fetch_invoice_metadata(self, invoice_code): return self.meta

    def fetch_invoice_details(self, invoice_code):
        return [{
            'product_id': 100, 'quantity': 5, 'unit_id': 10, 'unit_name': 'Cái',
            'unit_price': Decimal('10000'), 'total_price': Decimal('50000'), 'total_cogs_amount': Decimal('20000.0000')
        }]

    def update_invoice_status(self, invoice_code, status, cancel_reason=None):
        self.meta['status'] = status


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.sale_repo = FakeSaleRepo()
        self.invoice_history_repo = FakeInvoiceHistoryRepository()
        self._snapshot = None

    def __enter__(self):
        self._snapshot = {
            'inv': copy.deepcopy(self.inventory_repo.inventory),
            'tx': copy.deepcopy(self.inventory_repo.stock_transactions),
            'status': self.invoice_history_repo.meta['status']
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:  # Kích hoạt khôi phục snapshot tài chính
            self.inventory_repo.inventory = self._snapshot['inv']
            self.inventory_repo.stock_transactions = self._snapshot['tx']
            self.invoice_history_repo.meta['status'] = self._snapshot['status']


@pytest.fixture
def uow(): return FakeUnitOfWork()


@pytest.fixture
def history_service(uow): return InvoiceHistoryServiceImpl(lambda: uow)


# ==========================================
# BỘ TEST INVARIANTS CHÍNH THỨC
# ==========================================
def test_cancel_invoice_transaction_rollback_on_unexpected_system_error(history_service, uow):
    """TC_Inv_01: Đảm bảo tính ACID - Đứt kết nối database giữa chừng phải rollback sạch sẽ kho bãi"""

    def mock_db_crash(*args, **kwargs):
        raise RuntimeError("CSDL mất kết nối đột ngột!")

    uow.invoice_history_repo.update_invoice_status = mock_db_crash

    with pytest.raises(Exception, match="CSDL mất kết nối đột ngột"):
        history_service.execute_cancel_invoice("HD-001", "Hủy đơn")

    # Kiểm chứng tính bất biến: Kho không được cộng hàng rác, hóa đơn giữ nguyên status gốc
    assert uow.inventory_repo.inventory[100]['quantity'] == 0
    assert uow.invoice_history_repo.meta['status'] == 'COMPLETED'
    assert len(uow.inventory_repo.stock_transactions) == 0


def test_cancel_invoice_triggers_anomaly_clearance_when_empty_stock_holds_value(history_service, uow):
    """
    TC_Inv_02: Kiểm chứng Bước 2 - Dọn rác khi kho trống đọng tiền rác.
    Bối cảnh: Số lượng kho vật lý = 0 nhưng két tài chính còn kẹt 3.500đ rác làm tròn.
    Mong đợi:
    - Bắn INSERT log DATA_CORRECTION mang giá trị chênh lệch âm (-3500đ).
    - Ép môi trường két về 0đ trước khi nhận 20.000đ giá vốn hoàn trả.
    """
    # GIVEN: Tạo môi trường đọng rác tài chính ngoại vi
    uow.inventory_repo.inventory[100] = {'quantity': 0, 'total_value': Decimal('3500.0000')}

    # WHEN: Thực thi hủy hóa đơn hoàn trả 5 sản phẩm (giá vốn hoàn 20k)
    history_service.execute_cancel_invoice("HD-001", "Khách trả toàn bộ")

    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # THEN: 1. Số lượng tăng lên 5, tổng tiền kho mới phải bằng đúng 20k trọn vẹn (không kẹt 3.5k rác)
    assert db_inv.inventory[100]['quantity'] == 5
    assert db_inv.inventory[100]['total_value'] == Decimal('20000.0000')
    assert db_prod.products[100]['cost_price'] == Decimal('4000.0000')  # MAC pha loãng: 20k / 5 = 4k

    # 2. Audit Trail: Bắt buộc sinh ra đúng 2 dòng dịch chuyển kho
    assert len(db_inv.stock_transactions) == 2

    # Dòng log 1 phải là dòng hốt rác kế toán ngoại vi
    clearance_log = db_inv.stock_transactions[0]
    assert clearance_log['type'] == 'DATA_CORRECTION'
    assert clearance_log['qty'] == 0
    assert clearance_log['variance_amount'] == Decimal('-3500.0000')
    assert "Điều chỉnh dọn rác giá trị tồn đọng khi kho trống" in clearance_log['note']
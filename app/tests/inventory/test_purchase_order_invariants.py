import pytest
import copy
from decimal import Decimal
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl


# ==========================================
# SETUP FAKE REPOS & UOW (CÓ CHỨC NĂNG ROLLBACK)
# ==========================================
class FakeSupplierRepo:
    def exists_by_id(self, supplier_id): return True


class FakeProductRepo:
    def get_product_detail_for_import(self, product_id):
        return {
            'id': 100,
            'name': 'Bút bi',
            'is_active': True,
            'base_unit_id': 10,
            'conversion_unit_id': None,
            'cost_price': 4000
        }

    def update_cost_price(self, product_id, new_mac): pass


class FakeInventoryRepo:
    def __init__(self):
        # Trạng thái ban đầu: Đang có 50 cây bút bi
        self.inventory = {100: {"quantity": 50, "total_value": Decimal('200000')}}
        self.purchase_orders = []
        self.purchase_order_items = []
        self.stock_transactions = []
        self.next_po_id = 1

    def get_inventory_status(self, product_id): return self.inventory.get(product_id)

    def update_inventory_status(self, product_id, qty, val): self.inventory[product_id] = {"quantity": qty,
                                                                                           "total_value": val}

    def create_purchase_order(self, po_data):
        po_data['id'] = self.next_po_id
        self.purchase_orders.append(po_data)
        self.next_po_id += 1
        return po_data['id']

    def create_purchase_order_item(self, item): self.purchase_order_items.append(item)

    def add_stock_transaction(self, trans): self.stock_transactions.append(trans)


class FakeUnitOfWork:
    """Fake UOW có khả năng Snapshot để Rollback như DB thật"""

    def __init__(self, override_inventory_repo=None):
        self.supplier_repo = FakeSupplierRepo()
        self.product_repo = FakeProductRepo()
        self.inventory_repo = override_inventory_repo or FakeInventoryRepo()
        self._snapshot = None

    def __enter__(self):
        # SNAPSHOT: Chụp ảnh toàn bộ dữ liệu của InventoryRepo trước khi giao dịch
        self._snapshot = copy.deepcopy(self.inventory_repo.__dict__)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nếu có Exception bay ra (exc_type != None) -> ROLLBACK
        if exc_type is not None:
            self.inventory_repo.__dict__ = self._snapshot


# ==========================================
# EST CASE: TÍNH TOÀN VẸN TRANSACTION (ROLLBACK)
# ==========================================
def test_transaction_rollback_when_db_fails():
    """TC_Inv_01: Nếu đang lưu dở mà bị lỗi mạng/DB -> Phải Rollback sạch sẽ"""

    # 1. Tạo một Repo Đột biến (Buggy) để giả lập lỗi đứt cáp mạng ở bước cuối cùng
    class BuggyInventoryRepo(FakeInventoryRepo):
        def add_stock_transaction(self, trans_data):
            raise ConnectionError("Đứt cáp mạng, rớt Database đột ngột!")

    buggy_repo = BuggyInventoryRepo()
    uow_factory = lambda: FakeUnitOfWork(override_inventory_repo=buggy_repo)
    service = InventoryServiceImpl(uow_factory)

    dto = PurchaseOrderCreateDTO(
        supplier_id=1, note="Test Rollback",
        items=[PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)]
    )

    # 2. WHEN: Thực hiện gọi hàm nhập kho
    with pytest.raises(Exception) as exc_info:
        service.create_purchase_order(dto)

    # Đảm bảo Service đã bọc lỗi lại thành "Lỗi hệ thống..."
    assert "Lỗi hệ thống" in str(exc_info.value)
    assert "Đứt cáp mạng" in str(exc_info.value)

    # 3. THEN: KIỂM CHỨNG BẤT BIẾN (ROLLBACK THÀNH CÔNG)
    # Tồn kho phải giữ nguyên 50 cây, KHÔNG ĐƯỢC cộng thêm 10 cây
    assert buggy_repo.inventory[100]['quantity'] == 50
    # Tổng tiền kho phải giữ nguyên 200k, KHÔNG ĐƯỢC cộng thêm 50k
    assert buggy_repo.inventory[100]['total_value'] == Decimal('200000')
    # Không có bất kỳ phiếu nhập nào được sinh ra (Rác)
    assert len(buggy_repo.purchase_orders) == 0
    assert len(buggy_repo.purchase_order_items) == 0


# ==========================================
# TEST CASE: GIỚI HẠN TOÁN HỌC (MAC CALCULATOR)
# ==========================================
def test_mathematical_limits_prevent_negative_inventory():
    """TC_Inv_02: Chặn đứng mọi nỗ lực nhập hàng khi phát hiện kho đang bị âm"""

    repo = FakeInventoryRepo()
    # GIVEN: Cố tình set tồn kho hiện tại đang bị Âm (ví dụ do lỗi xuất khống trước đó)
    repo.inventory[100] = {"quantity": -5, "total_value": Decimal('-20000')}

    uow_factory = lambda: FakeUnitOfWork(override_inventory_repo=repo)
    service = InventoryServiceImpl(uow_factory)

    dto = PurchaseOrderCreateDTO(
        supplier_id=1, note="Test Toán học",
        items=[PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)]
    )

    # WHEN: Gọi hàm lưu phiếu nhập
    with pytest.raises(Exception) as exc_info:
        service.create_purchase_order(dto)

    # THEN: Kiểm chứng
    # Lỗi phải được bắn ra từ MACCalculator
    assert "Hàm này không dùng cho kho âm" in str(exc_info.value)

    # Tồn kho vẫn bị đóng băng ở -5, không được phép cộng lên thành +5
    assert repo.inventory[100]['quantity'] == -5
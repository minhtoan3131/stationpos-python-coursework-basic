import pytest
import copy
from decimal import Decimal
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl
from app.core.exceptions.validation_exception import ValidationException


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

    def get_conversion_info(self, product_id, unit_id):
        # Service sẽ gọi hàm này để check tỷ lệ quy đổi
        return None


class FakeUnitOfWork:
    """Fake UOW có khả năng Snapshot để Rollback như DB thật"""

    def __init__(self, override_inventory_repo=None):
        self.supplier_repo = FakeSupplierRepo()
        self.product_repo = FakeProductRepo()
        self.inventory_repo = override_inventory_repo or FakeInventoryRepo()
        self._snapshot = None

    def __enter__(self):
        # SNAPSHOT: Chụp ảnh toàn bộ dữ liệu của các bảng repo trước khi giao dịch
        self._snapshot = {
            'inventory': copy.deepcopy(self.inventory_repo.inventory),
            'purchase_orders': copy.deepcopy(self.inventory_repo.purchase_orders),
            'purchase_order_items': copy.deepcopy(self.inventory_repo.purchase_order_items),
            'stock_transactions': copy.deepcopy(self.inventory_repo.stock_transactions)
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nếu có Exception bay ra (exc_type != None) -> ROLLBACK hoàn tác sạch sẽ số liệu về snapshot cũ
        if exc_type is not None:
            self.inventory_repo.inventory = self._snapshot['inventory']
            self.inventory_repo.purchase_orders = self._snapshot['purchase_orders']
            self.inventory_repo.purchase_order_items = self._snapshot['purchase_order_items']
            self.inventory_repo.stock_transactions = self._snapshot['stock_transactions']


# ==========================================
# TEST CASE: TÍNH TOÀN VẸN TRANSACTION (ROLLBACK)
# ==========================================
def test_transaction_rollback_when_db_fails():
    """TC_Inv_01: Nếu đang lưu dở mà bị lỗi mạng/DB -> Phải Rollback sạch sẽ số liệu về ban đầu"""

    # 1. Tạo một Repo Đột biến (Buggy) để giả lập lỗi rớt kết nối Database ở bước cuối cùng khi ghi log dịch chuyển
    class BuggyInventoryRepo(FakeInventoryRepo):
        def add_stock_transaction(self, trans_data):
            # Nếu là dòng log dịch chuyển IMPORT vật lý thông thường thì ép crash hệ thống
            if trans_data.get('type') == 'IMPORT':
                raise ConnectionError("Đứt cáp mạng, rớt Database đột ngột!")
            super().add_stock_transaction(trans_data)

    buggy_repo = BuggyInventoryRepo()
    uow_factory = lambda: FakeUnitOfWork(override_inventory_repo=buggy_repo)
    service = InventoryServiceImpl(uow_factory)

    dto = PurchaseOrderCreateDTO(
        supplier_id=1, note="Test Rollback",
        items=[PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)]
    )

    # 2. WHEN: Thực hiện gọi hàm nhập kho
    with pytest.raises(ConnectionError) as exc_info:
        service.create_purchase_order(dto)

    assert "Đứt cáp mạng" in str(exc_info.value)

    # 3. THEN: KIỂM CHỨNG BẤT BIẾN (ROLLBACK THÀNH CÔNG)
    # Tồn kho phải giữ nguyên trạng thái ban đầu là 50 cây, KHÔNG ĐƯỢC phép lưu 60 cây lẻ lẻ
    assert buggy_repo.inventory[100]['quantity'] == 50
    # Tổng tiền kho phải giữ nguyên 200k, KHÔNG ĐƯỢC phép cộng thêm 50k
    assert buggy_repo.inventory[100]['total_value'] == Decimal('200000')
    # Không có bất kỳ một dòng dữ liệu rác nào được lưu lại trong bảng Master hay bảng Detail
    assert len(buggy_repo.purchase_orders) == 0
    assert len(buggy_repo.purchase_order_items) == 0
    assert len(buggy_repo.stock_transactions) == 0


# ==========================================
# TEST CASE: GIỚI HẠN TOÁN HỌC (CHẶN BÁN KHỐNG / KHO ÂM)
# ==========================================
def test_mathematical_limits_prevent_negative_inventory():
    """TC_Inv_02: Chặn đứng mọi nỗ lực nhập hàng khi phát hiện kho đang bị âm trái phép"""

    repo = FakeInventoryRepo()
    # GIVEN: Cố tình tạo trạng thái lỗi hệ thống từ trước: Kho bị âm -5 cây
    repo.inventory[100] = {"quantity": -5, "total_value": Decimal('-20000')}

    uow_factory = lambda: FakeUnitOfWork(override_inventory_repo=repo)
    service = InventoryServiceImpl(uow_factory)

    dto = PurchaseOrderCreateDTO(
        supplier_id=1, note="Test Toán học",
        items=[PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)]
    )

    # WHEN: Gọi hàm lưu phiếu nhập, Service phải đóng gói thành ValidationException để UI bắn thông báo
    with pytest.raises(ValidationException) as exc_info:
        service.create_purchase_order(dto)

    # THEN: Kiểm chứng chốt chặn an toàn nghiệp vụ
     Xác minh đúng câu thông báo tiếng Việt nghiệp vụ hiển thị cho user
    assert "Phát hiện trạng thái kho âm bất hợp lệ (Mô hình bán khống chưa được kích hoạt)." in str(exc_info.value)

    # Tồn kho vật lý bắt buộc phải bị đóng băng hoàn toàn ở con số -5, tuyệt đối không được xử lý tiếp
    assert repo.inventory[100]['quantity'] == -5
    assert repo.inventory[100]['total_value'] == Decimal('-20000')
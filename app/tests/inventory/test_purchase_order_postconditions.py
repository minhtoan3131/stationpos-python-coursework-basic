import pytest
from decimal import Decimal
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl


# ==========================================
# SETUP FAKE DB & REPOSITORIES (STATE-BASED)
# ==========================================
class FakeSupplierRepo:
    def exists_by_id(self, supplier_id): return True


class FakeProductRepo:
    def __init__(self):
        # Giả lập bảng Products trên DB
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'is_active': True, 'base_unit_id': 10, 'conversion_unit_id': None,
                  'conversion_ratio': None, 'cost_price': 4000},
            200: {'id': 200, 'name': 'Giấy A4', 'is_active': True, 'base_unit_id': 20, 'conversion_unit_id': 21,
                  'conversion_ratio': 5, 'cost_price': 0}
        }

    def get_product_detail_for_import(self, product_id):
        return self.products.get(product_id)

    def update_cost_price(self, product_id, new_mac):
        # Lưu lại giá MAC mới để tí nữa Assert
        self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        # Giả lập các bảng dữ liệu liên quan đến Tồn kho & Audit
        self.inventory = {
            100: {"quantity": 50, "total_value": Decimal('200000')},  # Bút bi đang có 50 cây, tổng giá trị 200k
            200: {"quantity": 0, "total_value": Decimal('0')}  # Giấy A4 chưa nhập bao giờ
        }
        self.purchase_orders = []
        self.purchase_order_items = []
        self.stock_transactions = []
        self.next_po_id = 1

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {"quantity": 0, "total_value": 0})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {"quantity": new_qty, "total_value": new_total_value}

    def create_purchase_order(self, po_data):
        po_data['id'] = self.next_po_id
        self.purchase_orders.append(po_data)
        self.next_po_id += 1
        return po_data['id']

    def create_purchase_order_item(self, item_data):
        self.purchase_order_items.append(item_data)

    def add_stock_transaction(self, trans_data):
        self.stock_transactions.append(trans_data)


class FakeUnitOfWork:
    def __init__(self):
        self.supplier_repo = FakeSupplierRepo()
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURE KHỞI TẠO SERVICE
# ==========================================
@pytest.fixture
def uow():
    """Tạo ra UOW để test có thể truy cập trực tiếp vào Fake DB nhằm Assert"""
    return FakeUnitOfWork()


@pytest.fixture
def inventory_service(uow):
    return InventoryServiceImpl(lambda: uow)


# ==========================================
# BÀI TEST CHÍNH: KIỂM CHỨNG TOÀN BỘ POST-CONDITIONS
# ==========================================
def test_create_purchase_order_happy_path_state_changes(inventory_service, uow):
    # ==========================================
    # GIVEN: Chuẩn bị Giỏ hàng nhập kho hoàn hảo
    # ==========================================
    # Món 1: Nhập 10 cây Bút bi (ĐVT Cơ bản) x giá 5,000 = 50,000
    item_base = PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)

    # Món 2: Nhập 2 Lốc Giấy A4 (ĐVT Quy đổi: 1 Lốc = 5 Ream) x giá 100,000 = 200,000
    item_conv = PurchaseOrderItemDTO(product_id=200, unit_id=21, quantity=2, unit_price=100000)

    dto = PurchaseOrderCreateDTO(supplier_id=1, note="Nhập hàng tháng 10", items=[item_base, item_conv])

    # ==========================================
    # WHEN: Thực thi luồng nhập kho duy nhất
    # ==========================================
    saved_po_id = inventory_service.create_purchase_order(dto)

    # ==========================================
    # THEN: Kiểm chứng Trạng thái hệ thống (Post-Conditions)
    # ==========================================
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # --- TC_Post_01: Kiểm tra Bút bi (Nhập ĐVT Cơ bản) ---
    # Tồn kho cũ: 50, Nhập thêm: 10 -> Mới: 60
    assert db_inv.inventory[100]['quantity'] == 60
    # Giá trị cũ: 200k, Nhập thêm: 50k -> Tổng giá trị mới: 250k
    assert db_inv.inventory[100]['total_value'] == Decimal('250000.0000')
    # Giá vốn MAC mới = 250,000 / 60 = 4,166.6667
    assert db_prod.products[100]['cost_price'] == Decimal('4166.6667')

    # --- TC_Post_02: Kiểm tra Giấy A4 (Nhập ĐVT Quy đổi) ---
    # Nhập 2 Lốc (1 Lốc = 5) -> Số lượng cơ bản cộng vào kho phải là 10
    assert db_inv.inventory[200]['quantity'] == 10
    assert db_inv.inventory[200]['total_value'] == Decimal('200000.0000')

    # --- TC_Post_03: Kiểm tra Dấu vết Audit Trail ---
    # 1. Bảng purchase_orders: Phải sinh ra 1 phiếu với tổng tiền = 50k + 200k = 250k
    assert len(db_inv.purchase_orders) == 1
    assert db_inv.purchase_orders[0]['total_amount'] == 250000

    # 2. Bảng purchase_order_items: Phải lưu đúng 2 dòng chi tiết
    assert len(db_inv.purchase_order_items) == 2
    assert db_inv.purchase_order_items[0]['total'] == 50000
    assert db_inv.purchase_order_items[1]['total'] == 200000

    # 3. Bảng stock_transactions: Phải có 2 dòng log IMPORT trỏ đúng về ID phiếu nhập
    assert len(db_inv.stock_transactions) == 2
    # Transaction của giấy A4 (Quy đổi) phải ghi nhận số lượng thay đổi là 10, không phải 2
    assert db_inv.stock_transactions[1]['product_id'] == 200
    assert db_inv.stock_transactions[1]['qty'] == 10
    assert db_inv.stock_transactions[1]['ref_id'] == saved_po_id
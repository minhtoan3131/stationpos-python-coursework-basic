import pytest
from decimal import Decimal
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl


# ==========================================
# SETUP FAKE DB & REPOSITORIES (NÂNG CẤP CHẶT CHẼ)
# ==========================================
class FakeSupplierRepo:
    def exists_by_id(self, supplier_id):
        return True


class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'is_active': True, 'base_unit_id': 10, 'conversion_unit_id': None},
            200: {'id': 200, 'name': 'Giấy A4', 'is_active': True, 'base_unit_id': 20, 'conversion_unit_id': 21}
        }

    def get_product_detail_for_import(self, product_id):
        return self.products.get(product_id)

    def update_cost_price(self, product_id, new_mac):
        self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {
            100: {"quantity": 50, "total_value": Decimal('200000.0000')},
            200: {"quantity": 0, "total_value": Decimal('0.0000')}
        }
        self.purchase_orders = []
        self.purchase_order_items = []
        self.stock_transactions = []
        self.next_po_id = 1

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {"quantity": 0, "total_value": Decimal('0.0000')})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {"quantity": new_qty, "total_value": new_total_value}

    def create_purchase_order(self, po_data):
        po_data['id'] = self.next_po_id
        # Đồng bộ logic gốc: Tự động gán status mặc định là COMPLETED nếu thiếu
        if 'status' not in po_data:
            po_data['status'] = 'COMPLETED'
        self.purchase_orders.append(po_data)
        self.next_po_id += 1
        return po_data['id']

    def create_purchase_order_item(self, item_data):
        self.purchase_order_items.append(item_data)

    def add_stock_transaction(self, trans_data):
        #  Giả lập các cột mặc định dựa trên DB schema thực tế
        if 'variance_amount' not in trans_data:
            trans_data['variance_amount'] = Decimal('0.0000')
        if 'note' not in trans_data:
            trans_data['note'] = None
        self.stock_transactions.append(trans_data)

    def get_conversion_info(self, product_id, unit_id):
        if product_id == 200 and unit_id == 21:
            return {'ratio': 5}
        return None


class FakeUnitOfWork:
    def __init__(self):
        self.supplier_repo = FakeSupplierRepo()
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def inventory_service(uow):
    return InventoryServiceImpl(lambda: uow)


# ==========================================
# BÀI TEST CHÍNH THỨC (ĐÃ SIẾT CHẶT QUY TRÌNH)
# ==========================================

def test_create_purchase_order_happy_path_state_changes(inventory_service, uow):
    """Kiểm chứng Bước 1, Bước 2 & Bước 4 của Luồng 1"""
    item_base = PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=10, unit_price=5000)
    item_conv = PurchaseOrderItemDTO(product_id=200, unit_id=21, quantity=2, unit_price=100000)
    dto = PurchaseOrderCreateDTO(supplier_id=1, note="Nhập hàng tháng 10", items=[item_base, item_conv])

    saved_po_id = inventory_service.create_purchase_order(dto)

    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # --- Đã siết chặt kiểm tra làm tròn 4 chữ số thập phân cho cả 2 bảng ---
    assert db_inv.inventory[100]['quantity'] == 60
    assert db_inv.inventory[100]['total_value'] == Decimal('250000.0000')
    assert db_prod.products[100]['cost_price'] == Decimal('4166.6667')

    assert db_inv.inventory[200]['quantity'] == 10
    assert db_inv.inventory[200]['total_value'] == Decimal('200000.0000')

    # --- Bước 2: Kiểm chứng bắt buộc Header trạng thái COMPLETED ---
    assert len(db_inv.purchase_orders) == 1
    assert db_inv.purchase_orders[0]['total_amount'] == 250000.0
    assert db_inv.purchase_orders[0]['status'] == 'COMPLETED'

    assert len(db_inv.purchase_order_items) == 2
    assert db_inv.purchase_order_items[0]['total_price'] == 50000.0
    assert db_inv.purchase_order_items[1]['total_price'] == 200000.0


def test_create_purchase_order_should_trigger_anomaly_clearance_log_and_exact_math(inventory_service, uow):
    """
    BƯỚC 3 - Trường hợp A: Bóc tách rác tiền khi kho vật lý trống trơn (old_qty == 0).
    Kiểm chứng nghiêm ngặt:
    1. Reset môi trường sạch (old_total_value = 0) trước khi nạp lô mới.
    2. Sinh bút toán điều chỉnh bất thường với giá trị âm (-garbage_value).
    3. Ghi chú log hạch toán rõ ràng theo đúng văn bản đặc tả.
    """
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo

    # GIVEN: Số lượng kho bằng 0 nhưng còn tồn đọng 15.000đ tiền rác kế toán
    db_inv.inventory[100] = {"quantity": 0, "total_value": Decimal('15000.0000')}

    # Nhập mới lô hàng 5 cái x đơn giá 10.000đ = 50.000đ
    item = PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=5, unit_price=10000)
    dto = PurchaseOrderCreateDTO(supplier_id=1, note="Nhập dọn rác", items=[item])

    # ACT
    saved_po_id = inventory_service.create_purchase_order(dto)

    # THEN: Kiểm chứng giá trị kho được reset sạch sẽ về 0đ trước khi cộng 50.000đ mới vào
    assert db_inv.inventory[100]['quantity'] == 5
    assert db_inv.inventory[100]['total_value'] == Decimal('50000.0000')  # Đảm bảo hốt sạch 15.000đ rác
    assert db_prod.products[100]['cost_price'] == Decimal('10000.0000')  # MAC không bị lệch

    # Kiểm chứng chi tiết Nhật ký giao dịch (Audit Trail)
    assert len(db_inv.stock_transactions) == 2

    # --- KIỂM CHỨNG CHẶT CHẼ HÀNH ĐỘNG 1 & 2 CỦA TRƯỜNG HỢP A ---
    clearance_log = db_inv.stock_transactions[0]
    assert clearance_log['product_id'] == 100
    assert clearance_log['qty'] == 0  # Biến động hàng vật lý bắt buộc bằng 0
    assert clearance_log['type'] == 'DATA_CORRECTION'  # Loại log điều chỉnh
    assert clearance_log['ref_id'] == saved_po_id

     Xác minh con số âm triệt tiêu rác tài chính và chuỗi ghi chú đặc tả
    assert clearance_log['variance_amount'] == Decimal('-15000.0000')
    assert clearance_log['note'] == "Điều chỉnh dọn rác giá trị tồn đọng khi kho trống"

    # Kiểm tra log nhập kho vật lý kế tiếp
    import_log = db_inv.stock_transactions[1]
    assert import_log['type'] == 'IMPORT'
    assert import_log['qty'] == 5
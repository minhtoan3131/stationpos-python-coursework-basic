import pytest
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES (CƠ SỞ DỮ LIỆU RAM)
# # ==========================================
class FakeProductRepo:
    def __init__(self):
        # Dữ liệu mồi: Sản phẩm Bút bi (ID=10) không có quy đổi
        self.products = {
            10: {'id': 10, 'conversion_unit_id': None, 'conversion_ratio': None}
        }

    def get_product_detail_for_import(self, product_id):
        return self.products.get(product_id)


class FakeInventoryRepo:
    def __init__(self):
        # Dữ liệu mồi: Tồn kho hiện tại của Bút bi (ID=10) chỉ còn 50 cây
        self.inventory = {
            10: {'quantity': 50, 'total_value': Decimal('25000')}
        }

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id)


class FakePOHistoryRepo:
    def __init__(self):
        # Dữ liệu mồi: Bảng danh sách phiếu (Master)
        self.po_master_table = {
            1: {'id': 1, 'status': 'COMPLETED'},  # Phiếu hợp lệ để trừ kho
            2: {'id': 2, 'status': 'CANCELLED'}  # Phiếu đã bị hủy từ trước
        }
        # Dữ liệu mồi: Bảng chi tiết mặt hàng (Items)
        self.po_items_table = {
            # Phiếu 1 lúc nhập đã nhập tới 100 cây Bút bi (ID=10)
            1: [{'product_id': 10, 'sku': 'SP01', 'quantity': 100, 'unit_id': 1, 'total_price': 50000}],
            2: []
        }

    def get_purchase_order_by_id(self, po_id):
        return self.po_master_table.get(po_id)

    def get_purchase_order_items(self, po_id):
        return self.po_items_table.get(po_id, [])


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.po_history_repo = FakePOHistoryRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURE (BƠM SERVICE VÀO TEST)
# ==========================================
@pytest.fixture
def po_service():
    """Khởi tạo Service tiêm kèm Fake UnitOfWork"""
    return PurchaseOrderHistoryServiceImpl(lambda: FakeUnitOfWork())


# ==========================================
#  TEST CASE CHÍNH (PARAMETRIZE VÉT CẠN 4 RÀNG BUỘC)
# ==========================================
@pytest.mark.parametrize("po_id, cancel_reason, expected_error_msg", [
    # TC_Pre_01: Lý do trống rỗng
    (1, "", "Vui lòng nhập lý do hủy phiếu."),

    # TC_Pre_01: Lý do toàn khoảng trắng
    (1, "   ", "Vui lòng nhập lý do hủy phiếu."),

    # TC_Pre_02: Phiếu không tồn tại (ID 999 không có trong Fake Repo)
    (999, "Ghi nhầm", "Không tìm thấy phiếu nhập này."),

    # TC_Pre_03: Phiếu đã hủy từ trước (ID 2 có status = CANCELLED)
    (2, "Muốn hủy lại", "Phiếu nhập này đã được hủy trước đó."),

    # TC_Pre_04: Kho không đủ để trừ (Phiếu 1 nhập 100 cây, nhưng Fake Kho hiện chỉ còn 50 cây)
    (1, "Hàng hỏng", "không đủ số lượng tồn để hủy"),
])
def test_cancel_purchase_order_preconditions_fails(po_service, po_id, cancel_reason, expected_error_msg):
    """Kiểm tra toàn bộ các kịch bản bị từ chối khi hủy phiếu"""

    # WHEN & THEN: Gọi hàm Service và bắt ValidationException
    with pytest.raises(ValidationException) as exc_info:
        po_service.cancel_purchase_order(po_id, cancel_reason)

    # Kiểm chứng: Dòng thông báo lỗi văng ra phải chứa thông điệp ta kỳ vọng
    assert expected_error_msg in str(exc_info.value)
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES (CƠ SỞ DỮ LIỆU RAM)
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {
            10: {'id': 10, 'conversion_unit_id': None, 'conversion_ratio': None}
        }

    def get_product_detail_for_import(self, product_id):
        return self.products.get(product_id)


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {
            10: {'quantity': 50, 'total_value': Decimal('25000')}
        }

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id)


class FakePOHistoryRepo:
    def __init__(self):
        # Mốc thời gian phiếu nhập: 2 tiếng trước
        self.po_time = datetime.now() - timedelta(hours=2)

        self.po_master_table = {
            1: {'id': 1, 'code': 'PO-001', 'status': 'COMPLETED', 'created_at': self.po_time},
            2: {'id': 2, 'code': 'PO-002', 'status': 'CANCELLED', 'created_at': self.po_time},
            3: {'id': 3, 'code': 'PO-003', 'status': 'COMPLETED', 'created_at': self.po_time}
        }

        self.po_items_table = {
            1: [{'product_id': 10, 'sku': 'SP01', 'quantity': 100, 'unit_id': 1, 'total_price': 50000}],
            2: [],
            3: [{'product_id': 10, 'sku': 'SP01', 'quantity': 10, 'unit_id': 1, 'total_price': 5000}]
        }

        self.has_subsequent_sale = False

    def get_purchase_order_by_id(self, po_id):
        return self.po_master_table.get(po_id)

    def get_purchase_order_items(self, po_id):
        return self.po_items_table.get(po_id, [])

    def has_subsequent_delivery_transactions(self, product_id, po_created_at):
        # Giả lập Chốt chặn 2: Trả về kết quả phát hiện giao dịch xuất kho sau thời điểm lập phiếu
        return self.has_subsequent_sale


class FakeUnitOfWork:
    def __init__(self, override_history_repo=None):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.po_history_repo = override_history_repo or FakePOHistoryRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
#  TEST CASE CHÍNH (PARAMETRIZE VÉT CẠN CÁC RÀNG BUỘC)
# ==========================================
@pytest.mark.parametrize("po_id, cancel_reason, mock_sale_state, expected_error_msg", [
    # TC_Pre_01: Lý do trống rỗng
    (1, "", False, "Vui lòng nhập lý do hủy phiếu."),

    # TC_Pre_01: Lý do toàn khoảng trắng
    (1, "   ", False, "Vui lòng nhập lý do hủy phiếu."),

    # TC_Pre_02: Phiếu không tồn tại
    (999, "Ghi nhầm", False, "Không tìm thấy phiếu nhập này."),

    # TC_Pre_03: Phiếu đã hủy từ trước
    (2, "Muốn hủy lại", False, "Phiếu nhập này đã được hủy trước đó."),

    # TC_Pre_04: Chốt chặn 1 - Kho không đủ để trừ ngược (Gây âm kho)
    (1, "Hàng hỏng", False, "Hủy phiếu nhập sẽ làm kho bị âm, vi phạm chính sách!"),
])
def test_cancel_purchase_order_preconditions_fails(po_id, cancel_reason, mock_sale_state, expected_error_msg):
    """Kiểm tra toàn bộ các kịch bản bị từ chối dựa trên điều kiện tiên quyết (Chốt chặn 1)"""
    repo = FakePOHistoryRepo()
    repo.has_subsequent_sale = mock_sale_state
    po_service = PurchaseOrderHistoryServiceImpl(lambda: FakeUnitOfWork(repo))

    with pytest.raises(ValidationException) as exc_info:
        po_service.cancel_purchase_order(po_id, cancel_reason)

    assert expected_error_msg in str(exc_info.value)


def test_cancel_purchase_order_blocks_when_subsequent_sale_exists():
    """TC_Pre_05: Chốt chặn 2 - Chặn đứng hủy phiếu nếu hàng hóa đã bị xuất bán sau thời điểm nhập"""
    # GIVEN: Thiết lập giỏ hàng PN3 hợp lệ (chỉ trừ 10, kho đang có 50 -> dư sức trừ kho)
    repo = FakePOHistoryRepo()
    # Kích hoạt quả bom Chốt chặn 2: Báo hiệu đã xuất bán hàng hóa sau mốc tạo phiếu này
    repo.has_subsequent_sale = True

    po_service = PurchaseOrderHistoryServiceImpl(lambda: FakeUnitOfWork(repo))

    # WHEN & THEN: Thực thi hủy và kiểm chứng hệ thống đóng băng giao dịch bảo vệ lịch sử MAC
    with pytest.raises(ValidationException) as exc_info:
        po_service.cancel_purchase_order(po_id=3, cancel_reason="Muốn trả hàng")

    assert "đã bị xuất bán hoặc điều chuyển sau thời điểm nhập" in str(exc_info.value)
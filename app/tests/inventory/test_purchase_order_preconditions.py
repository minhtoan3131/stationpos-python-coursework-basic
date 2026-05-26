import pytest
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES & UOW (BỘ NHỚ RAM)
# ==========================================
class FakeSupplierRepo:
    def exists_by_id(self, supplier_id):
        # Giả lập: Chỉ có Nhà cung cấp ID = 1 là tồn tại trong hệ thống
        return supplier_id == 1


class FakeProductRepo:
    def get_product_detail_for_import(self, product_id):
        # Giả lập Database chứa 2 sản phẩm
        db = {
            100: {'id': 100, 'name': 'Bút bi', 'is_active': True, 'base_unit_id': 10, 'conversion_unit_id': 11},
            101: {'id': 101, 'name': 'Vở nắp', 'is_active': False, 'base_unit_id': 10, 'conversion_unit_id': None}
        }
        return db.get(product_id)


class FakeInventoryRepo:
    def __init__(self):
        self.po_created = False

    def create_purchase_order(self, po_data):
        self.po_created = True  # Đánh dấu trạng thái đã tạo
        return 999


class FakeUnitOfWork:
    """Giả lập Context Manager của DB (Tự động Commit/Rollback)"""

    def __init__(self):
        self.supplier_repo = FakeSupplierRepo()
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # ==========================================


# FIXTURES (BƠM DEPENDENCY)
# ==========================================
@pytest.fixture
def inventory_service():
    """Khởi tạo service với Fake UnitOfWork (Không dùng Mock framework)"""
    uow_factory = lambda: FakeUnitOfWork()
    return InventoryServiceImpl(uow_factory)


@pytest.fixture
def valid_dto():
    """Tạo một DTO chuẩn mực, hợp lệ hoàn toàn để làm gốc (Happy Path)"""
    item = PurchaseOrderItemDTO(product_id=100, unit_id=10, quantity=50, unit_price=5000)
    return PurchaseOrderCreateDTO(supplier_id=1, note="Nhập hàng tháng 10", items=[item])


# ==========================================
# 3. CÁC HÀM PHÁ DTO ĐỂ TẠO LỖI
# ==========================================
def invalidate_empty_items(dto): dto.items = []


def invalidate_zero_qty(dto): dto.items[0].quantity = 0


def invalidate_negative_price(dto): dto.items[0].unit_price = -100


def invalidate_supplier(dto): dto.supplier_id = 99


def invalidate_duplicate_items(dto):
    # Add thêm 1 dòng y hệt dòng cũ (cùng product_id)
    dto.items.append(PurchaseOrderItemDTO(product_id=100, unit_id=11, quantity=5, unit_price=100000))


def invalidate_inactive_product(dto): dto.items[0].product_id = 101  # Vở nắp đã ngừng KD


def invalidate_wrong_unit(dto): dto.items[0].unit_id = 99  # Sai ĐVT

def invalidate_blank_price(dto):
    dto.items[0].unit_price = None  # Giả lập để trống giá gõ từ UI

def invalidate_zero_price(dto):
    dto.items[0].unit_price = 0  # Giá bằng 0


# ==========================================
# TEST CASE CHÍNH (PARAMETRIZE - DATA DRIVEN)
# ==========================================
@pytest.mark.parametrize("scenario, modifier_func, expected_error_msg", [
    ("TC_Pre_01: Items trống", invalidate_empty_items, "Phiếu nhập không có sản phẩm nào"),
    ("TC_Pre_02: SL <= 0", invalidate_zero_qty, "Số lượng nhập phải lớn hơn 0"),
    ("TC_Pre_03: Giá < 0", invalidate_negative_price, "phải > 0"),
    ("TC_Pre_04: Supplier sai", invalidate_supplier, "Nhà cung cấp không tồn tại"),
    ("TC_Pre_06: SP ngừng KD", invalidate_inactive_product, "không tồn tại hoặc đã ngừng kinh doanh"),
    ("TC_Pre_07: Sai ĐVT", invalidate_wrong_unit, "Đơn vị tính chọn cho sản phẩm"),
    ("TC_Pre_08: Giá trống", invalidate_blank_price, "đang để trống giá"),
    ("TC_Pre_09: Giá bằng 0", invalidate_zero_price, "phải > 0"),
])
def test_create_purchase_order_validation_fails(inventory_service, valid_dto, scenario, modifier_func,
                                                expected_error_msg):
    # GIVEN: Lấy DTO hợp lệ và dùng hàm 'modifier_func' để bẻ gãy luật
    modifier_func(valid_dto)

    # WHEN & THEN: Gọi service và bắt ValidationException
    with pytest.raises(ValidationException) as exc_info:
        inventory_service.create_purchase_order(valid_dto)

    # Kiểm chứng thông báo lỗi có chứa từ khóa mong đợi
    assert expected_error_msg in str(exc_info.value)
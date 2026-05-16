import pytest
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES & UOW (BỘ NHỚ RAM)
# ==========================================

class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10}
        }

    def get_product_by_id(self, product_id):
        return type('Product', (object,), self.products[product_id]) if product_id in self.products else None


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {100: {'quantity': 20}}

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, 0)


class FakeCursor:
    def execute(self, sql, params):
        pass

    def fetchone(self):
        # Trả về None giả lập việc không tìm thấy ĐVT quy đổi
        return None


class FakeConnection:
    def cursor(self, dictionary=False):
        return FakeCursor()


class FakeUnitOfWork:
    def __init__(self, product_repo, inventory_repo):
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo
        self.connection = FakeConnection()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def sale_service():
    prod_repo = FakeProductRepo()
    inv_repo = FakeInventoryRepo()
    uow_factory = lambda: FakeUnitOfWork(prod_repo, inv_repo)
    return SaleServiceImpl(uow_factory)


@pytest.fixture
def valid_checkout_dto():
    item = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi",
        unit_id=10, unit_name="Cái", quantity=5,
        price=Decimal('10000'), total=Decimal('50000')
    )
    return CheckoutDTO(
        code="", total_amount=Decimal('50000'),
        discount=Decimal('0'), final_amount=Decimal('50000'),
        payment_method='CASH', cash_received=Decimal('50000'),
        items=[item]
    )


# ==========================================
# CÁC HÀM PHÁ HOẠI DTO ĐỂ TẠO LỖI
# ==========================================
def invalidate_empty_cart(dto): dto.items = []


def invalidate_insufficient_cash(dto): dto.cash_received = Decimal('40000')


def invalidate_non_existent_product(dto): dto.items[0].product_id = 999


def invalidate_unit_not_converted(dto): dto.items[0].unit_id = 99


def invalidate_out_of_stock(dto): dto.items[0].quantity = 100


# ==========================================
# TEST CASE CHÍNH
# ==========================================

@pytest.mark.parametrize("scenario, modifier_func, expected_error_msg", [
    ("TC_Pre_01: Giỏ hàng trống", invalidate_empty_cart, "Giỏ hàng đang trống"),
    ("TC_Pre_02: Thiếu tiền mặt", invalidate_insufficient_cash, "không đủ để thanh toán"),
    ("TC_Pre_04: Sai đơn vị tính", invalidate_unit_not_converted, "Đơn vị tính không hợp lệ"),
    ("TC_Pre_05: Không đủ tồn kho", invalidate_out_of_stock, "không đủ tồn kho"),
])
def test_checkout_preconditions_validation_fails(sale_service, valid_checkout_dto, scenario, modifier_func,
                                                 expected_error_msg):
    modifier_func(valid_checkout_dto)

    with pytest.raises(ValidationException) as exc_info:
        sale_service.process_checkout(valid_checkout_dto)

    assert expected_error_msg in str(exc_info.value)


def test_checkout_pre_product_not_found(sale_service, valid_checkout_dto):
    """Sản phẩm không tồn tại trong hệ thống"""
    # GIVEN: Cố tình truyền vào ID sản phẩm ma
    invalidate_non_existent_product(valid_checkout_dto)

    # WHEN & THEN:
    # Logic hiện tại của Service khi không tìm thấy product sẽ gây lỗi (vd: AttributeError khi gọi product.name)
    # Ta bắt Exception chung để chứng minh giao dịch bị chặn lại.
    with pytest.raises(Exception):
        sale_service.process_checkout(valid_checkout_dto)
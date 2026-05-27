import pytest
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES CHUẨN KIẾN TRÚC
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10}
        }

    def get_product_by_id(self, product_id):
        if product_id in self.products:
            class Product:
                id = self.products[product_id]['id']
                name = self.products[product_id]['name']
                base_unit_id = self.products[product_id]['base_unit_id']

            return Product()
        return None


class FakeInventoryRepo:
    def __init__(self):
        # Thiết lập tồn kho ban đầu là 20 cái
        self.inventory = {100: {'quantity': 20, 'total_value': Decimal('80000.0000')}}

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {'quantity': 0, 'total_value': Decimal('0.0000')})

    def update_inventory_status(self, product_id, new_qty, new_total_value): pass

    def add_stock_transaction(self, trans_data) -> int: return 1

    def link_stock_transactions_to_invoice(self, transaction_ids, invoice_id): pass

    def get_conversion_info(self, product_id, unit_id):
        # Trả về None giả lập việc đơn vị tính quy đổi không hợp lệ/không tồn tại
        return None


class FakeSaleRepo:
    def create_invoice(self, checkout_data): return 1

    def create_invoice_items(self, invoice_id, items): pass

    def add_invoice_log(self, invoice_id, action, note): pass


class FakeUnitOfWork:
    def __init__(self, product_repo, inventory_repo):
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo
        self.sale_repo = FakeSaleRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES KHỞI TẠO
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
        price=Decimal('10000'), total=Decimal('50000'), cost_price=Decimal('4000')
    )
    return CheckoutDTO(
        code="", total_amount=Decimal('50000'), discount=Decimal('0'), final_amount=Decimal('50000'),
        payment_method='CASH', cash_received=Decimal('50000'), items=[item]
    )


# ==========================================
# CÁC HÀM BẺ GÃY LUẬT DỮ LIỆU
# ==========================================
def invalidate_empty_cart(dto): dto.items = []


def invalidate_insufficient_cash(dto): dto.cash_received = Decimal('40000')


def invalidate_non_existent_product(dto): dto.items[0].product_id = 999


def invalidate_unit_not_converted(dto): dto.items[0].unit_id = 99


def invalidate_out_of_stock(dto): dto.items[0].quantity = 100


# ==========================================
# BỘ TEST CASES ĐIỀU KIỆN TIÊN QUYẾT
# ==========================================
@pytest.mark.parametrize("scenario, modifier_func, expected_error_msg", [
    ("TC_Pre_01: Giỏ hàng trống", invalidate_empty_cart, "Giỏ hàng đang trống"),
    ("TC_Pre_02: Thiếu tiền mặt", invalidate_insufficient_cash, "không đủ để thanh toán"),
    ("TC_Pre_04: Sai đơn vị tính", invalidate_unit_not_converted, "Đơn vị tính không hợp lệ"),
    ("TC_Pre_05: Không đủ tồn kho", invalidate_out_of_stock, "không đủ tồn kho để thực hiện giao dịch"),
])
def test_checkout_preconditions_validation_fails(sale_service, valid_checkout_dto, scenario, modifier_func,
                                                 expected_error_msg):
    modifier_func(valid_checkout_dto)

    with pytest.raises(ValidationException) as exc_info:
        sale_service.process_checkout(valid_checkout_dto)

    assert expected_error_msg in str(exc_info.value)


def test_checkout_pre_product_not_found(sale_service, valid_checkout_dto):
    """TC_Pre_06: Kiểm tra chốt chặn an toàn khi sản phẩm không tồn tại trong danh mục hệ thống"""
    invalidate_non_existent_product(valid_checkout_dto)

    with pytest.raises(ValidationException) as exc_info:
        sale_service.process_checkout(valid_checkout_dto)

     Khớp chuẩn xác thông điệp lỗi quy đổi đơn vị tính của sản phẩm ma từ Service
    assert "Đơn vị tính không hợp lệ" in str(exc_info.value)
    assert "ID 999" in str(exc_info.value)
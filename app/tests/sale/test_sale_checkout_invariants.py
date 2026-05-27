import pytest
import copy
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# SETUP FAKE REPOSITORIES & UOW
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10}
        }

    def get_product_by_id(self, product_id):
        if product_id in self.products:
            # Mô phỏng một Object Product có các thuộc tính nguyên bản
            class Product:
                id = self.products[product_id]['id']
                name = self.products[product_id]['name']
                base_unit_id = self.products[product_id]['base_unit_id']
            return Product()
        return None


class FakeInventoryRepo:
    def __init__(self):
        self.inventory = {100: {'quantity': 50, 'total_value': Decimal('200000.0000')}}
        self.stock_transactions = []
        self.next_tx_id = 1

    def get_inventory_status(self, product_id):
        # Trả về dict cấu trúc chuẩn có khóa dòng FOR UPDATE ngầm định
        return self.inventory.get(product_id, {'quantity': 0, 'total_value': Decimal('0.0000')})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data) -> int:
        trans_data['id'] = self.next_tx_id
        self.stock_transactions.append(trans_data)
        self.next_tx_id += 1
        return trans_data['id']

    def link_stock_transactions_to_invoice(self, transaction_ids: list, invoice_id: int) -> None:
        """Gán chính xác reference_id cho danh sách ID log SALE cụ thể, tuyệt đối không quét mù"""
        for tx in self.stock_transactions:
            if tx['id'] in transaction_ids:
                tx['reference_id'] = invoice_id

    def get_conversion_info(self, product_id, unit_id):
        return None


class FakeSaleRepo:
    def __init__(self):
        self.invoices = []
        self.invoice_items = []
        self.invoice_logs = []
        self.next_invoice_id = 1

    def create_invoice(self, checkout_data):
        invoice = {'id': self.next_invoice_id, 'code': checkout_data.code, 'total_amount': checkout_data.total_amount}
        self.invoices.append(invoice)
        self.next_invoice_id += 1
        return invoice['id']

    def create_invoice_items(self, invoice_id, items):
        for item in items:
            self.invoice_items.append({'invoice_id': invoice_id, 'item': item})

    def add_invoice_log(self, invoice_id, action, note):
        self.invoice_logs.append({'invoice_id': invoice_id, 'action': action, 'note': note})


class FakeUnitOfWork:
    def __init__(self, override_sale_repo=None):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.sale_repo = override_sale_repo or FakeSaleRepo()

    def __enter__(self):
        self._inv_snapshot = copy.deepcopy(self.inventory_repo.__dict__)
        self._sale_snapshot = copy.deepcopy(self.sale_repo.__dict__)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.inventory_repo.__dict__ = self._inv_snapshot
            self.sale_repo.__dict__ = self._sale_snapshot


@pytest.fixture
def valid_checkout_dto():
    item = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi",
        unit_id=10, unit_name="Cái", quantity=5,
        price=Decimal('10000'), total=Decimal('50000'), cost_price=Decimal('4000')
    )
    return CheckoutDTO(
        code="", total_amount=Decimal('50000'), discount=Decimal('0'),
        final_amount=Decimal('50000'), payment_method='CASH', cash_received=Decimal('50000'), items=[item]
    )


# ==========================================
# BỘ TEST CASES KIỂM CHỨNG TÍNH BẤT BIẾN
# ==========================================
def test_transaction_rollback_when_db_fails(valid_checkout_dto):
    """TC_Inv_01: Đảm bảo tính ACID - Gặp sự cố đột ngột khi tạo hóa đơn phải hoàn tác sạch sẽ tồn kho"""
    class BuggySaleRepo(FakeSaleRepo):
        def create_invoice(self, checkout_data):
            raise ConnectionError("Mất kết nối cơ sở dữ liệu khi lưu hóa đơn Master!")

    buggy_repo = BuggySaleRepo()
    uow_factory = lambda: FakeUnitOfWork(override_sale_repo=buggy_repo)
    service = SaleServiceImpl(uow_factory)

    with pytest.raises(Exception, match="Mất kết nối cơ sở dữ liệu"):
        service.process_checkout(valid_checkout_dto)

    inv_repo = service.uow_factory().inventory_repo

    # Dữ liệu kho phải giữ nguyên vẹn, không bị khấu trừ lơ lửng
    assert inv_repo.inventory[100]['quantity'] == 50
    assert inv_repo.inventory[100]['total_value'] == Decimal('200000.0000')
    assert len(buggy_repo.invoices) == 0
    assert len(inv_repo.stock_transactions) == 0


def test_mathematical_limits_prevent_negative_inventory(valid_checkout_dto):
    """TC_Inv_02: Chốt chặn cấm bán khống - Số lượng mua vượt quá số lượng tồn vật lý phải bị từ chối ngay lập tức"""
    uow_factory = lambda: FakeUnitOfWork()
    service = SaleServiceImpl(uow_factory)

    # GIVEN: Khách mua 100 cây bút trong khi kho chỉ còn tồn 50 cây
    valid_checkout_dto.items[0].quantity = 100

    # WHEN & THEN
    with pytest.raises(ValidationException) as exc_info:
        service.process_checkout(valid_checkout_dto)

    assert "không đủ tồn kho để thực hiện giao dịch" in str(exc_info.value)

    inv_repo = service.uow_factory().inventory_repo
    sale_repo = service.uow_factory().sale_repo

    # Kiểm tra tính đóng băng: Không trừ kho, không sinh hóa đơn, không log dịch chuyển
    assert inv_repo.inventory[100]['quantity'] == 50
    assert len(sale_repo.invoices) == 0
    assert len(inv_repo.stock_transactions) == 0
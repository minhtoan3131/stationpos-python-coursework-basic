import copy
from unittest.mock import MagicMock

import pytest
from decimal import Decimal
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl


# ==========================================
# SETUP STATE-BASED FAKE REPOSITORIES
# ==========================================
class FakeProductRepo:
    def __init__(self):
        self.products = {
            100: {'id': 100, 'name': 'Bút bi', 'base_unit_id': 10},
            200: {'id': 200, 'name': 'Sổ tay', 'base_unit_id': 20}
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
        # Kho ban đầu: Bút bi có 50 cái, trị giá 200k. Sổ tay có 100 cuốn, trị giá 500k.
        self.inventory = {
            100: {'quantity': 50, 'total_value': Decimal('200000.0000')},
            200: {'quantity': 100, 'total_value': Decimal('500000.0000')}
        }
        self.stock_transactions = []
        self.next_tx_id = 1

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {'quantity': 0, 'total_value': Decimal('0.0000')})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data) -> int:
        trans_data['id'] = self.next_tx_id
        trans_data['reference_id'] = None
        self.stock_transactions.append(trans_data)
        self.next_tx_id += 1
        return trans_data['id']

    def link_stock_transactions_to_invoice(self, transaction_ids: list, invoice_id: int) -> None:
        for tx in self.stock_transactions:
            if tx['id'] in transaction_ids:
                tx['reference_id'] = invoice_id

    def get_conversion_info(self, product_id, unit_id):
        # Mua Sổ tay (ID 200) bằng Hộp (ID 21) -> Tỷ lệ quy đổi là 10
        if product_id == 200 and unit_id == 21:
            return {'ratio': 10}
        return None


class FakeSaleRepo:
    def __init__(self):
        self.invoices = []
        self.invoice_items = []
        self.invoice_logs = []
        self.next_invoice_id = 88  # Giả lập ID hóa đơn thật phát sinh từ DB tự tăng

    def create_invoice(self, checkout_data):
        invoice = {
            'id': self.next_invoice_id, 'code': checkout_data.code,
            'total_amount': checkout_data.total_amount, 'status': 'COMPLETED'
        }
        self.invoices.append(invoice)
        return invoice['id']

    def create_invoice_items(self, invoice_id, items):
        for item in items:
            self.invoice_items.append({'invoice_id': invoice_id, 'item': copy.deepcopy(item)})

    def add_invoice_log(self, invoice_id, action, note):
        self.invoice_logs.append({'invoice_id': invoice_id, 'action': action, 'note': note})


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.sale_repo = FakeSaleRepo()
        self.activity_log_repo = MagicMock()


    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def uow(): return FakeUnitOfWork()


@pytest.fixture
def sale_service(uow): return SaleServiceImpl(lambda: uow)


# ==========================================
# BỘ TEST CASES HẬU ĐIỀU KIỆN (POST-CONDITIONS)
# ==========================================
def test_checkout_happy_path_state_changes_and_cogs_allocation(sale_service, uow):
    """TC_Post_01 -> 05: Kiểm tra toàn luồng biến động kho lùi toán học và chốt snapshot COGS"""
    item_base = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi", unit_id=10, unit_name="Cái",
        quantity=5, price=Decimal('10000'), total=Decimal('50000'), cost_price=Decimal('4000')
    )
    item_conv = CartItemDTO(
        product_id=200, sku="SP02", name="Sổ tay", unit_id=21, unit_name="Hộp",
        quantity=2, price=Decimal('60000'), total=Decimal('120000'), cost_price=Decimal('50000')
    )
    dto = CheckoutDTO(
        code="", total_amount=Decimal('170000'), discount=Decimal('0'), final_amount=Decimal('170000'),
        payment_method='CASH', cash_received=Decimal('200000'), items=[item_base, item_conv]
    )

    saved_invoice_code = sale_service.process_checkout(dto)

    db_sale = uow.sale_repo
    db_inv = uow.inventory_repo

    # --- TC_Post_01 & 02: Khấu trừ tồn kho vật lý chính xác theo đơn vị cơ bản ---
    assert db_inv.inventory[100]['quantity'] == 45  # 50 - 5 = 45
    assert db_inv.inventory[200]['quantity'] == 80  # 100 - (2 Hộp x 10) = 80

    # --- TC_Post_03: Ép giá trị tiền kho tròn trịa (Định dạng Decimal 4 số) ---
    assert db_inv.inventory[100]['total_value'] == Decimal('180000.0000')  # 45 x 4k
    assert db_inv.inventory[200]['total_value'] == Decimal('400000.0000')  # 80 x 5k

    # --- TC_Post_04: Chốt snapshot COGS lịch sử gánh sai số giải trình lên bảng details ---
    assert len(db_sale.invoice_items) == 2
    # COGS mặt hàng Bút bi dòng này: 5 cái x 4.000đ = 20.000đ
    assert db_sale.invoice_items[0]['item'].total_cogs_amount == Decimal('20000.0000')
    # COGS mặt hàng Sổ tay dòng này: 20 cuốn x 5.000đ = 100.000đ
    assert db_sale.invoice_items[1]['item'].total_cogs_amount == Decimal('100000.0000')

    # --- TC_Post_05: Audit Trail chuẩn xác theo danh sách ID liên kết, không quét mù ---
    assert len(db_inv.stock_transactions) == 2
    assert db_inv.stock_transactions[0]['qty'] == -5
    assert db_inv.stock_transactions[0]['reference_id'] == 88  # Khớp chính xác ID hóa đơn

    assert db_inv.stock_transactions[1]['qty'] == -20
    assert db_inv.stock_transactions[1]['reference_id'] == 88  # Khớp chính xác ID hóa đơn


def test_checkout_forces_absolute_zero_and_invoice_absorbs_decimal_garbage(sale_service, uow):
    """
    TC_Post_06: Tâm điểm Luồng 2 - Ép giá trị tiền kho về 0 khi cạn hàng.
    Bối cảnh: Kho còn đúng 3 cái bút bi với tổng tiền đọng sai số float lịch sử là 15.000,0002đ. Khách mua nốt cả 3 cái.
    Mong đợi:
    1. Tiền kho mới rơi về 0.0000đ tuyệt đối, triệt tiêu hoàn toàn rác.
    2. Hóa đơn chi tiết nhận chỉ số COGS nghịch đảo gánh trọn vẹn sai số: 15.000,0002đ.
    """
    db_inv = uow.inventory_repo
    db_sale = uow.sale_repo

    # Ép kho cũ dính rác thập phân cực đoan
    db_inv.inventory[100] = {'quantity': 3, 'total_value': Decimal('15000.0002')}

    item = CartItemDTO(
        product_id=100, sku="SP01", name="Bút bi", unit_id=10, unit_name="Cái",
        quantity=3, price=Decimal('10000'), total=Decimal('30000'), cost_price=Decimal('5000')
    )
    dto = CheckoutDTO(
        code="", total_amount=Decimal('30000'), discount=Decimal('0'), final_amount=Decimal('30000'),
        payment_method='CASH', cash_received=Decimal('30000'), items=[item]
    )

    sale_service.process_checkout(dto)

    # ASSERT 1: Tiền kho vật lý bắt buộc phải cạn sạch không kẹt rác
    assert db_inv.inventory[100]['quantity'] == 0
    assert db_inv.inventory[100]['total_value'] == Decimal('0.0000')

    # ASSERT 2: Phương pháp toán học nghịch đảo dồn toàn bộ 15.000,0002đ vào cột COGS chi tiết
    assert db_sale.invoice_items[0]['item'].total_cogs_amount == Decimal('15000.0002')
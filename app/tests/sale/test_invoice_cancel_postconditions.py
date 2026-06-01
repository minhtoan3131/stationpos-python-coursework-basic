from unittest.mock import MagicMock

import pytest
from decimal import Decimal
from datetime import datetime
from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl


# ==========================================
# SETUP STATE-BASED FAKE REPOSITORIES
# ==========================================
class FakeProductRepo:
    def __init__(self):
        # Trạng thái ban đầu: Sản phẩm Bút bi (ID 100) đang có giá vốn MAC = 5.000đ
        self.products = {
            100: {'id': 100, 'sku': 'SP01', 'name': 'Bút bi Thiên Long', 'cost_price': Decimal('5000.0000')}
        }

    def get_product_by_id(self, product_id):
        if product_id in self.products:
            class Product:
                id = self.products[product_id]['id']
                sku = self.products[product_id]['sku']
                name = self.products[product_id]['name']

            return Product()
        return None

    def update_cost_price(self, product_id, new_mac):
        # Ghi nhận lại giá vốn pha loãng mới phục vụ lệnh quyết toán Assert
        self.products[product_id]['cost_price'] = new_mac


class FakeInventoryRepo:
    def __init__(self):
        # Két sắt tồn kho hiện tại: Đang có sẵn 15 cái với tổng trị giá là 75.000đ (75k / 15 = 5k MAC)
        self.inventory = {
            100: {'quantity': 15, 'total_value': Decimal('75000.0000')}
        }
        self.stock_transactions = []

        self.conversion_info = {
            10: {'ratio': Decimal('1')},  # unit_id = 10 đại diện cho Cái (Lẻ)
            20: {'ratio': Decimal('10')},  # unit_id = 20 đại diện cho Hộp (Sỉ 1)
            30: {'ratio': Decimal('100')}  # unit_id = 30 đại diện cho Thùng (Sỉ 2)
        }

    def get_inventory_status(self, product_id):
        return self.inventory.get(product_id, {'quantity': 0, 'total_value': Decimal('0.0000')})

    def update_inventory_status(self, product_id, new_qty, new_total_value):
        self.inventory[product_id] = {'quantity': new_qty, 'total_value': new_total_value}

    def add_stock_transaction(self, trans_data):
        self.stock_transactions.append(trans_data)

    def get_conversion_info(self, product_id, unit_id):
        return self.conversion_info.get(unit_id, {'ratio': Decimal('1')})


class FakeSaleRepo:
    def __init__(self):
        self.invoice_logs = []

    def add_invoice_log(self, invoice_id, action, note):
        self.invoice_logs.append({'invoice_id': invoice_id, 'action': action, 'note': note})


class FakeInvoiceHistoryRepository:
    def __init__(self):
        # Hóa đơn mồi: Đang ở trạng thái COMPLETED
        self.meta = {
            'id': 99,
            'code': 'HD-20260527-777',
            'status': 'COMPLETED',
            'created_at': datetime.now(),
            'final_amount': Decimal('50000'),
            'payment_method': 'CASH',
            'cash_received': Decimal('50000'),
            'cancel_reason': None
        }

    def fetch_invoice_metadata(self, invoice_code):
        if invoice_code == self.meta['code']:
            return self.meta
        return {}

    def fetch_invoice_details(self, invoice_code):
        # Chi tiết hóa đơn mồi: Khách đã mua 5 cái bút bi,
        # Giá vốn snapshot chốt cứng trong lịch sử là 3.000đ/cái -> Tổng hoàn vốn COGS = 15.000đ
        if invoice_code == self.meta['code']:
            return [{
                'product_id': 100,
                'quantity': 5,
                'unit_id': 10,  # Khai báo mặc định là đơn vị lẻ (Cái)
                'sku': 'SP01',
                'product_name': 'Bút bi Thiên Long',
                'unit_name': 'Cái',
                'unit_price': Decimal('10000'),
                'total_price': Decimal('50000'),
                'total_cogs_amount': Decimal('15000.0000')
            }]
        return []

    def update_invoice_status(self, invoice_code, status, cancel_reason=None):
        if invoice_code == self.meta['code']:
            self.meta['status'] = status
            self.meta['cancel_reason'] = cancel_reason
            return True
        return False


class FakeUnitOfWork:
    def __init__(self):
        self.product_repo = FakeProductRepo()
        self.inventory_repo = FakeInventoryRepo()
        self.sale_repo = FakeSaleRepo()
        self.invoice_history_repo = FakeInvoiceHistoryRepository()
        self.activity_log_repo = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ==========================================
# FIXTURES KHỞI TẠO LUỒNG KIỂM THỬ
# ==========================================
@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def history_service(uow):
    return InvoiceHistoryServiceImpl(lambda: uow)


# ==========================================
# BỘ BÀI TEST CASES HẬU ĐIỀU KIỆN (POST-CONDITIONS)
# ==========================================

def test_cancel_invoice_happy_path_state_changes_and_mac_dilution(history_service, uow):
    """
    TC_Post_01 -> 04: Đảm bảo tăng hàng, hoàn tiền vốn gánh rác, pha loãng MAC danh mục và lưu Audit Trail sạch.

    Bối cảnh toán học:
    - Kho đang có: 15 cái với tổng tiền tồn là 75.000đ (MAC hiện hành = 5.000đ).
    - Hóa đơn hoàn trả: 5 cái với giá vốn chốt lịch sử là 3.000đ/cái -> Tổng tiền hoàn trả là 15.000đ.
    - Kết quả mong đợi:
      + Số lượng mới = 15 + 5 = 20 cái.
      + Giá trị kho mới = 75.000đ + 15.000đ = 90.000đ.
      + Giá MAC danh mục mới bị pha loãng = 90.000đ / 20 = 4.500đ (đã giảm lùi từ mốc 5.000đ).
    """
    invoice_code = "HD-20260527-777"
    cancel_reason = "Khách hàng đổi ý, trả lại nguyên hộp chưa bóc"

    # WHEN: Kích hoạt thực thi nghiệp vụ hoàn trả Luồng 4
    result = history_service.execute_cancel_invoice(invoice_code, cancel_reason)

    # THEN: Xác minh toàn bộ hệ quả để lại trên CSDL
    assert result is True

    db_po = uow.invoice_history_repo
    db_inv = uow.inventory_repo
    db_prod = uow.product_repo
    db_sale = uow.sale_repo

    # --- TC_Post_01: Kiểm chứng biến động trạng thái Master Hóa đơn ---
    assert db_po.meta['status'] == 'CANCELLED'
    assert db_po.meta['cancel_reason'] == cancel_reason

    # --- TC_Post_02: Phục hồi số lượng kho vật lý (Cộng dồn tuyệt đối) ---
    assert db_inv.inventory[100]['quantity'] == 20

    # --- TC_Post_03: Pha loãng giá trị tài chính kho và giá vốn danh mục sản phẩm ---
    # Tổng tiền kho mới phải làm tròn chuẩn 4 chữ số thập phân (ROUND_HALF_UP)
    assert db_inv.inventory[100]['total_value'] == Decimal('90000.0000')
    # Giá vốn MAC danh mục mới bắt buộc bị kéo tụt pha loãng về mốc 4.500đ
    assert db_prod.products[100]['cost_price'] == Decimal('4500.0000')

    # --- TC_Post_04: Sổ cái Audit Trail lưu vết phân lớp chuẩn chỉ ---
    # 1. Log thao tác hệ thống hóa đơn gốc
    assert len(db_sale.invoice_logs) == 1
    assert db_sale.invoice_logs[0]['action'] == 'CANCEL'
    assert "Hủy hóa đơn tại Nhật ký" in db_sale.invoice_logs[0]['note']

    # 2. Nhật ký biến động kho mang số lượng Dương (Tăng hàng vật lý do khách trả)
    assert len(db_inv.stock_transactions) == 1
    log_stock = db_inv.stock_transactions[0]
    assert log_stock['product_id'] == 100
    assert log_stock['qty'] == 5  # Số lượng dương thể hiện vector tăng trưởng hoàn hàng
    assert log_stock['type'] == 'ANOMALY_ADJUSTMENT'  # Khớp với cấu trúc enum bảng dịch chuyển
    assert log_stock['variance_amount'] == Decimal('0.0000')
    assert log_stock['ref_id'] == 99  # Liên kết chính xác khóa chính ID của hóa đơn gốc
    assert "Nhập hàng trả lại từ hóa đơn bị hủy" in log_stock['note']


@pytest.mark.parametrize("sold_unit, sold_qty, conversion_ratio, expected_returned_base_qty", [
    ("Cái", 5, Decimal('1'), 5),  # Kịch bản lẻ: Hoàn nguyên 5 cái
    ("Hộp", 2, Decimal('10'), 20),  # Kịch bản sỉ 1: Mua 2 hộp (mỗi hộp 10 cái) -> Phải hoàn 20 cái vào kho
    ("Thùng", 1, Decimal('100'), 100),  # Kịch bản sỉ 2: Mua 1 thùng (mỗi thùng 100 cái) -> Phải hoàn 100 cái vào kho
])
def test_cancel_invoice_should_convert_multi_level_uom_to_base_unit_correctly(
        history_service, uow, sold_unit, sold_qty, conversion_ratio, expected_returned_base_qty
):
    """
    KỲ VỌNG KIỂM TOÁN: Dù khách mua bằng đơn vị sỉ hay lẻ, khi hủy đơn hoàn hàng,
    hạ tầng kho phải quy đổi chính xác về Số Lượng Cơ Bản nhỏ nhất trước khi cộng dồn vào két.
    """
    invoice_code = "HD-20260527-777"
    uow.invoice_history_repo.meta['code'] = invoice_code

    # Ánh xạ từ Tên đơn vị sang ID tương ứng phục vụ môi trường Fake Repo ---
    unit_id_map = {"Cái": 10, "Hộp": 20, "Thùng": 30}
    target_unit_id = unit_id_map.get(sold_unit, 10)

    # Tiếp tế cấu hình tỷ lệ quy đổi động trực tiếp vào bộ nhớ RAM của Fake Repo theo từng Test Case
    uow.inventory_repo.conversion_info[target_unit_id] = {'ratio': conversion_ratio}

    # Giả lập bản ghi chi tiết hóa đơn lưu thông tin đơn vị sỉ/lẻ thực tế
    uow.invoice_history_repo.fetch_invoice_details = lambda code: [{
        'product_id': 100,
        'unit_id': target_unit_id,  # Đưa unit_id vào giỏ hàng mồi để triệt tiêu KeyError
        'quantity': sold_qty,
        'unit_name': sold_unit,
        'total_cogs_amount': Decimal('15000.0000')
    }]

    # Thiết lập trạng thái kho ban đầu trống trơn (0 sản phẩm)
    uow.inventory_repo.inventory[100] = {'quantity': 0, 'total_value': Decimal('0.0000')}

    # 2. ACT
    history_service.execute_cancel_invoice(invoice_code, "Giảng viên kiểm tra quy đổi UOM")

    # 3. ASSERT: Số lượng hoàn kho cuối cùng BẮT BUỘC phải là số lượng đã quy đổi về đơn vị lẻ
    actual_returned_qty = uow.inventory_repo.inventory[100]['quantity']

    assert actual_returned_qty == expected_returned_base_qty, \
        f"Lỗi! Hủy {sold_qty} {sold_unit} phải trả về {expected_returned_base_qty} Cái, thực tế lại trả về {actual_returned_qty}"
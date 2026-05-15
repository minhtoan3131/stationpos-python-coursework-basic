import pytest
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl

# ==========================================
# SETUP FAKE REPO & UOW
# ==========================================
class FakeInventoryRepo:
    def get_inventory_list_data(self, search_keyword=None):
        # Giả lập kết quả trả về từ câu lệnh JOIN 4 bảng SQL
        data = [
            {'product_id': 1, 'sku': 'SP01', 'product_name': 'Bút bi', 'min_stock': 15, 'base_unit_name': 'Cây', 'conversion_unit_name': 'Hộp', 'conversion_ratio': 20, 'total_base_quantity': 25},
            {'product_id': 2, 'sku': 'SP02', 'product_name': 'Giấy A4', 'min_stock': 10, 'base_unit_name': 'Ream', 'conversion_unit_name': 'Thùng', 'conversion_ratio': 5, 'total_base_quantity': 5}
        ]
        if search_keyword:
            keyword = search_keyword.lower()
            return [item for item in data if keyword in item['product_name'].lower() or keyword in item['sku'].lower()]
        return data

class FakeUnitOfWork:
    def __init__(self): self.inventory_repo = FakeInventoryRepo()
    def __enter__(self): return self
    def __exit__(self, *args): pass

@pytest.fixture
def inventory_service():
    return InventoryServiceImpl(lambda: FakeUnitOfWork())

# ==========================================
# TEST CASES
# ==========================================
def test_uc1_get_all_without_keyword(inventory_service):
    # WHEN: Không truyền từ khóa
    result = inventory_service.get_inventory_list()
    # THEN: Lấy đủ 2 sản phẩm
    assert len(result) == 2

def test_uc1_search_by_keyword(inventory_service):
    # WHEN: Truyền từ khóa "Bút"
    result = inventory_service.get_inventory_list("Bút")
    # THEN: Chỉ lấy ra Bút bi
    assert len(result) == 1
    assert result[0].sku == "SP01"

def test_uc1_conversion_string_and_low_stock_logic(inventory_service):
    # WHEN: Lấy danh sách
    result = inventory_service.get_inventory_list()
    but_bi, giay_a4 = result[0], result[1]

    # THEN 1: Kiểm chứng chuỗi quy đổi (UnitConverter hoạt động đúng)
    # Bút bi có 25 cây (1 hộp 20 cây) -> 1 Hộp + 5 Cây
    assert but_bi.conversion_quantity_str == "1 Hộp + 5 Cây"
    # Giấy A4 có 5 ream (1 thùng 5 ream) -> 1 Thùng
    assert giay_a4.conversion_quantity_str == "1 Thùng"

    # THEN 2: Kiểm chứng cờ cảnh báo sắp hết hàng
    # Bút bi min=15, tồn=25 -> Không hết hàng
    assert but_bi.is_low_stock is False
    # Giấy A4 min=10, tồn=5 -> Đang bị thiếu
    assert giay_a4.is_low_stock is True
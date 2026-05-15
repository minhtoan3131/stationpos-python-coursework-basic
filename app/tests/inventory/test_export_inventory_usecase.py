import pytest
import os
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl


# ==========================================
# SETUP FAKE REPO
# ==========================================
class FakeInventoryRepo:
    def get_inventory_report_data(self):
        return [{
            'sku': 'SP01', 'product_name': 'Bút bi', 'unit_name': 'Cây',
            'cost_price': 5000, 'min_stock': 10, 'quantity': 50, 'total_value': 250000
        }]


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
def test_export_excel_success_with_tmp_path(inventory_service, tmp_path):
    """Xuất file Excel thành công không để lại rác"""

    # GIVEN: Khởi tạo đường dẫn vật lý trỏ vào thư mục ảo của Pytest
    export_file = tmp_path / "bao_cao_ton_kho_test.xlsx"

    # WHEN: Gọi Service
    result = inventory_service.export_inventory_to_excel(str(export_file))

    # THEN:
    # 1. Hàm trả về True
    assert result is True
    # 2. File Excel vật lý THỰC SỰ ĐƯỢC TẠO RA trong thư mục ảo (Chứng tỏ thư viện openpyxl đã chạy)
    assert os.path.exists(export_file)


def test_export_excel_throws_error_on_invalid_path(inventory_service):
    """Bắt lỗi ném ra từ thư viện xuất file khi thư mục cấm"""

    # GIVEN: Một đường dẫn không thể ghi được (Thư mục không tồn tại)
    invalid_path = "/thu_muc_ma_thuat_khong_ton_tai/bao_cao.xlsx"

    # WHEN & THEN:
    with pytest.raises(Exception) as exc_info:
        inventory_service.export_inventory_to_excel(invalid_path)

    # Service phải bọc lại được lỗi này
    assert "Có lỗi khi tạo file Excel" in str(exc_info.value)
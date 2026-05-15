import pytest
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl


# ==========================================
# SETUP FAKE REPO & UOW
# ==========================================
class FakeProductRepo:
    def search_products(self, keyword, category_id=None, supplier_id=None, is_active=True):
        data = [{'id': 100, 'name': 'Bút bi xanh'}, {'id': 101, 'name': 'Bút bi đỏ (Lỗi Database)'}]
        return [p for p in data if keyword.lower() in p['name'].lower()]

    def get_product_detail_for_import(self, product_id):
        if product_id == 100:
            return {'id': 100, 'sku': 'B01', 'name': 'Bút bi xanh', 'is_active': True}
        if product_id == 101:
            return None  # Giả lập DB bị mất record chi tiết do lỗi đồng bộ


class FakeUnitOfWork:
    def __init__(self): self.product_repo = FakeProductRepo()

    def __enter__(self): return self

    def __exit__(self, *args): pass


@pytest.fixture
def inventory_service():
    return InventoryServiceImpl(lambda: FakeUnitOfWork())


# ==========================================
# TEST CASES
# ==========================================
def test_uc3_empty_keyword_returns_fast(inventory_service):
    """ Từ khóa rỗng phải trả mảng rỗng ngay lập tức"""
    result = inventory_service.search_products_for_import("")
    assert result == []


def test_uc3_search_with_resilience_filtering(inventory_service):
    """Trả kết quả chuẩn và lọc bỏ sản phẩm bị mất chi tiết"""
    # GIVEN & WHEN: Tìm "Bút", Repo trả về 2 dòng, nhưng dòng 101 bị mất Detail
    result = inventory_service.search_products_for_import("Bút")

    # THEN: Service tự động nuốt lỗi, chỉ trả về đúng 1 DTO hợp lệ là 100
    assert len(result) == 1
    assert result[0].id == 100
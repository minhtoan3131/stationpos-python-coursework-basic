import pytest
from app.modules.product.entities.product import Product
from app.modules.product.repositories.impl.product_repository_impl import ProductRepositoryImpl


@pytest.fixture
def product_repo(db_test_connection):
    return ProductRepositoryImpl(db_test_connection)

@pytest.fixture
def sample_product():
    return Product(
        id=None, sku="SKU-001", name="Bút bi Test", barcode="1234567890123",
        category_id=1, supplier_id=1, base_unit_id=1,
        cost_price=3000, retail_price=5000, wholesale_price=4500,
        min_stock=10, description="Mô tả test", is_active=True, created_at=None
    )


# ---------------------------------------------------------
# CRUD CƠ BẢN & MAPPING DỮ LIỆU
# ---------------------------------------------------------

def test_create_and_get_product(product_repo, sample_product):
    # Test Create
    new_id = product_repo.create_product(sample_product)
    assert new_id > 0

    # Test Read & Mapping (Đảm bảo SQL dict map đúng sang Entity)
    product = product_repo.get_product_by_id(new_id)
    assert product is not None
    assert product.sku == "SKU-001"
    assert product.name == "Bút bi Test"
    assert float(product.retail_price) == 5000.0


def test_update_product(product_repo, sample_product):
    pid = product_repo.create_product(sample_product)

    # Thay đổi thông tin
    sample_product.id = pid
    sample_product.name = "Tên đã sửa"
    sample_product.retail_price = 6000

    success = product_repo.update_product(sample_product)
    assert success is True

    updated_product = product_repo.get_product_by_id(pid)
    assert updated_product.name == "Tên đã sửa"
    assert float(updated_product.retail_price) == 6000.0


def test_soft_delete_product(product_repo, sample_product):
    pid = product_repo.create_product(sample_product)

    success = product_repo.soft_delete_product(pid)
    assert success is True

    product = product_repo.get_product_by_id(pid)
    assert product.is_active == False  # Kiểm tra cờ is_active chuyển về 0


# ---------------------------------------------------------
# LOGIC TRUY VẤN ĐỘNG (DYNAMIC SQL)
# ---------------------------------------------------------

@pytest.mark.parametrize("keyword, cat_id, sup_id, expected_count", [
    ("SKU-001", None, None, 1),  # Tìm theo SKU
    ("Bút bi", None, None, 1),  # Tìm theo Tên
    (None, 1, None, 1),  # Lọc theo Category
    (None, 999, None, 0),  # Category không tồn tại
    ("KhongCo", None, None, 0),  # Keyword không khớp
])
def test_search_products_logic(product_repo, sample_product, keyword, cat_id, sup_id, expected_count):
    product_repo.create_product(sample_product)

    results = product_repo.search_products(
        keyword=keyword,
        category_id=cat_id,
        supplier_id=sup_id,
        is_active=True
    )
    assert len(results) == expected_count


# ---------------------------------------------------------
# XÁC THỰC TÍNH DUY NHẤT
# ---------------------------------------------------------

def test_exists_checks(product_repo, sample_product):
    # Chưa có sản phẩm
    assert product_repo.exists_by_sku("SKU-001") is False

    pid = product_repo.create_product(sample_product)

    # Đã có sản phẩm
    assert product_repo.exists_by_sku("SKU-001") is True
    assert product_repo.exists_by_barcode("1234567890123") is True

    # Test loại trừ ID (dùng cho Update)
    # Kiểm tra SKU của chính nó -> Trả về False (được phép giữ nguyên)
    assert product_repo.exists_by_sku_excluding_id("SKU-001", pid) is False

    # Tạo sản phẩm khác để test trùng chéo
    sample_product.sku = "SKU-002"
    product_repo.create_product(sample_product)
    assert product_repo.exists_by_sku_excluding_id("SKU-002", pid) is True
import pytest
from datetime import datetime

from app.modules.product.mappers.product_mapper import ProductMapper
from app.modules.product.entities.product import Product
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO


# ==========================================
# FIXTURES (Dữ liệu đầu vào)
# ==========================================

@pytest.fixture
def create_dto():
    return ProductCreateDTO(
        sku="SP_001",
        name="Bút bi",
        barcode="123456",
        category_id=1,
        supplier_id=2,
        base_unit_id=3,
        cost_price=3000.0,
        retail_price=5000.0,
        wholesale_price=4500.0,
        min_stock=10,
        description="Bút xanh",
        conversion_unit_id=4,
        conversion_ratio=12.0
    )


@pytest.fixture
def update_dto():
    return ProductUpdateDTO(
        product_id=99,
        sku="SP_001_UPDATED",
        name="Bút bi đỏ",
        barcode="654321",
        category_id=1,
        supplier_id=2,
        base_unit_id=3,
        cost_price=3500.0,
        retail_price=5500.0,
        wholesale_price=4800.0,
        min_stock=15,
        description="Bút đỏ",
        conversion_unit_id=4,
        conversion_ratio=12.0,
        is_active=False
    )

# Giả lập một dòng dữ liệu trả về từ câu lệnh SQL SELECT
@pytest.fixture
def db_row():
    return {
        "id": 1,
        "sku": "SP_001",
        "name": "Bút bi",
        "category_name": "Văn phòng phẩm",
        "unit_name": "Cây",
        "retail_price": 5000.0,
        "wholesale_price": 4500.0,
        "barcode": "123456",
        "supplier_name": "Thiên Long"
    }


@pytest.fixture
def entity_product():
    return Product(
        id=1,
        sku="SP_001",
        name="Bút bi",
        barcode="123456",
        category_id=1,
        supplier_id=2,
        base_unit_id=3,
        cost_price=3000.0,
        retail_price=5000.0,
        wholesale_price=4500.0,
        min_stock=10,
        description="Bút xanh",
        is_active=True,
        created_at=datetime.now()
    )


# ==========================================
# TEST CASES
# ==========================================

def test_to_entity_from_create_dto(create_dto):
    # WHEN
    entity = ProductMapper.to_entity_from_create_dto(create_dto)

    # THEN
    assert entity.id is None  # Tạo mới thì ID phải là None
    assert entity.sku == create_dto.sku
    assert entity.name == create_dto.name
    assert entity.barcode == create_dto.barcode
    assert entity.category_id == create_dto.category_id
    assert entity.supplier_id == create_dto.supplier_id
    assert entity.base_unit_id == create_dto.base_unit_id
    assert entity.cost_price == create_dto.cost_price
    assert entity.retail_price == create_dto.retail_price
    assert entity.wholesale_price == create_dto.wholesale_price
    assert entity.min_stock == create_dto.min_stock
    assert entity.description == create_dto.description
    assert entity.is_active is True  # Mặc định tạo mới phải là True
    assert entity.created_at is None

    # conversion_unit_id và ratio không nằm trong bảng products
    # nên mapper Entity sẽ không có thuộc tính này.


def test_to_entity_from_update_dto(update_dto):
    # WHEN
    entity = ProductMapper.to_entity_from_update_dto(update_dto)

    # THEN
    assert entity.id == update_dto.product_id  # Update thì ID phải được map
    assert entity.sku == update_dto.sku
    assert entity.name == update_dto.name
    assert entity.is_active == update_dto.is_active  # Update có thể đổi trạng thái
    assert entity.created_at is None


def test_to_product_list_dto(db_row):
    # WHEN
    dto = ProductMapper.to_product_list_dto(db_row)

    # THEN
    assert dto.id == db_row["id"]
    assert dto.sku == db_row["sku"]
    assert dto.name == db_row["name"]
    assert dto.category_name == db_row["category_name"]
    assert dto.unit_name == db_row["unit_name"]
    assert dto.retail_price == db_row["retail_price"]
    assert dto.wholesale_price == db_row["wholesale_price"]
    assert dto.barcode == db_row["barcode"]
    assert dto.supplier_name == db_row["supplier_name"]


def test_to_product_detail_dto_with_conversion(entity_product):
    # WHEN (Có thông tin quy đổi)
    dto = ProductMapper.to_product_detail_dto(
        product=entity_product,
        category_name="Văn phòng phẩm",
        supplier_name="Thiên Long",
        base_unit_name="Cây",
        conversion_unit_id=4,
        conversion_unit_name="Hộp",
        conversion_ratio=12.0
    )

    # THEN
    assert dto.id == entity_product.id
    assert dto.sku == entity_product.sku
    assert dto.category_name == "Văn phòng phẩm"
    assert dto.supplier_name == "Thiên Long"
    assert dto.base_unit_name == "Cây"
    assert dto.conversion_unit_id == 4
    assert dto.conversion_unit_name == "Hộp"
    assert dto.conversion_ratio == 12.0
    assert dto.cost_price == entity_product.cost_price


def test_to_product_detail_dto_without_conversion(entity_product):
    # WHEN (Sản phẩm không có quy đổi đơn vị -> Tham số truyền vào là None)
    dto = ProductMapper.to_product_detail_dto(
        product=entity_product,
        category_name="Văn phòng phẩm",
        supplier_name="Thiên Long",
        base_unit_name="Cây",
        conversion_unit_id=None,
        conversion_unit_name=None,
        conversion_ratio=None
    )

    # THEN
    assert dto.id == entity_product.id
    assert dto.base_unit_name == "Cây"
    assert dto.conversion_unit_id is None
    assert dto.conversion_unit_name is None
    assert dto.conversion_ratio is None
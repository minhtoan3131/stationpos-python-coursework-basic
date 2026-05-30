from app.modules.product.entities.product import Product
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.dtos.product_list_dto import ProductListDTO
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO


class ProductMapper:

    # =========================
    # CREATE DTO -> ENTITY
    # =========================

    @staticmethod
    def to_entity_from_create_dto(dto: ProductCreateDTO) -> Product:

        return Product(
            id=None,

            sku=dto.sku,
            name=dto.name,

            barcode=dto.barcode,

            category_id=dto.category_id,
            supplier_id=dto.supplier_id,

            base_unit_id=dto.base_unit_id,

            cost_price=dto.cost_price,
            retail_price=dto.retail_price,
            wholesale_price=dto.wholesale_price,

            min_stock=dto.min_stock,

            description=dto.description,

            is_active=True,

            created_at=None
        )

    # =========================
    # UPDATE DTO -> ENTITY
    # =========================

    @staticmethod
    def to_entity_from_update_dto(dto: ProductUpdateDTO) -> Product:

        return Product(
            id=dto.product_id,

            sku=dto.sku,
            name=dto.name,

            barcode=dto.barcode,

            category_id=dto.category_id,
            supplier_id=dto.supplier_id,

            base_unit_id=dto.base_unit_id,

            cost_price=dto.cost_price,
            retail_price=dto.retail_price,
            wholesale_price=dto.wholesale_price,

            min_stock=dto.min_stock,

            description=dto.description,

            is_active=dto.is_active,

            created_at=None
        )

    # =========================
    # ROW -> LIST DTO
    # =========================

    @staticmethod
    def to_product_list_dto(row: dict) -> ProductListDTO:
        return ProductListDTO(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            category_name=row["category_name"],
            unit_name=row["unit_name"],
            retail_price=row["retail_price"],
            wholesale_price=row["wholesale_price"],
            barcode=row["barcode"],
            supplier_name=row["supplier_name"],
            cost_price=float(row["cost_price"]) if row.get("cost_price") else 0.0,
            stock_qty=int(row["stock_qty"]) if row.get("stock_qty") is not None else 0,

            conversion_unit_name=row.get("conversion_unit_name"),
            conversion_ratio=row.get("conversion_ratio")
        )

    # =========================
    # ENTITY + JOIN DATA -> DETAIL DTO
    # =========================

    @staticmethod
    def to_product_detail_dto(
        product: Product,
        category_name: str,
        supplier_name: str,
        base_unit_name: str,
        conversion_unit_id: int | None,
        conversion_unit_name: str | None,
        conversion_ratio: float | None
    ) -> ProductDetailDTO:

        return ProductDetailDTO(
            id=product.id,

            sku=product.sku,
            barcode=product.barcode,

            name=product.name,
            description=product.description,

            category_id=product.category_id,
            category_name=category_name,

            supplier_id=product.supplier_id,
            supplier_name=supplier_name,

            base_unit_id=product.base_unit_id,
            base_unit_name=base_unit_name,

            cost_price=product.cost_price,
            retail_price=product.retail_price,
            wholesale_price=product.wholesale_price,

            conversion_unit_id=conversion_unit_id,
            conversion_unit_name=conversion_unit_name,
            conversion_ratio=conversion_ratio,

            min_stock=product.min_stock,

            is_active=product.is_active
        )
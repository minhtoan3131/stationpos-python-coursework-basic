from abc import ABC
from typing import List

from app.core.database.connection import DatabaseConnection
from app.core.database.transaction import TransactionManager
from app.modules.inventory.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl

from app.modules.product.services.product_service import ProductService

from app.modules.product.repositories.impl.product_repository_impl import ProductRepositoryImpl
from app.modules.product.repositories.impl.unit_conversion_repository_impl import UnitConversionRepositoryImpl

from app.modules.product.validators.product_validator import ProductValidator
from app.modules.product.mappers.product_mapper import ProductMapper

from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.modules.product.dtos.product_filter_dto import ProductFilterDTO
from app.modules.product.dtos.product_list_dto import ProductListDTO
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO
from app.modules.product.entities.unit_conversion import UnitConversion


class ProductServiceImpl(ProductService):
    def __init__(self):
        pass

    # =========================
    # PRODUCT LIST & SEARCH (READ - Không cần Transaction)
    # =========================

    def get_product_list(self) -> List[ProductListDTO]:
        connection = DatabaseConnection.get_connection()
        try:
            product_repo = ProductRepositoryImpl(connection)
            rows = product_repo.get_product_list()
            return [ProductMapper.to_product_list_dto(row) for row in rows]
        finally:
            connection.close()

    def search_products(self, filter_dto: ProductFilterDTO) -> List[ProductListDTO]:
        connection = DatabaseConnection.get_connection()
        try:
            product_repo = ProductRepositoryImpl(connection)
            rows = product_repo.search_products(
                keyword=filter_dto.keyword,
                category_id=filter_dto.category_id,
                supplier_id=filter_dto.supplier_id,
                is_active=filter_dto.is_active
            )
            return [ProductMapper.to_product_list_dto(row) for row in rows]
        finally:
            connection.close()

    def get_product_by_id(self, product_id: int) -> ProductDetailDTO:
        connection = DatabaseConnection.get_connection()
        try:
            product_repo = ProductRepositoryImpl(connection)
            unit_conv_repo = UnitConversionRepositoryImpl(connection)

            product = product_repo.get_product_by_id(product_id)
            if product is None:
                raise Exception("Không tìm thấy sản phẩm")

            # Lấy thông tin quy đổi (nếu có)
            conversion = unit_conv_repo.get_unit_conversion(product_id)

            return ProductMapper.to_product_detail_dto(
                product=product,
                category_name="",
                supplier_name="",
                base_unit_name="",
                conversion_unit_id=(conversion.to_unit_id if conversion else None),
                conversion_unit_name="",
                conversion_ratio=(conversion.ratio if conversion else None)
            )
        finally:
            connection.close()

    # =========================
    # CREATE
    # =========================

    def create_product(self, dto: ProductCreateDTO) -> int:
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            product_repo = ProductRepositoryImpl(connection)
            unit_conv_repo = UnitConversionRepositoryImpl(connection)
            validator = ProductValidator(product_repo)

            validator.validate_create(dto)

            product = ProductMapper.to_entity_from_create_dto(dto)

            product_id = product_repo.create_product(product)

            # Insert Đơn vị quy đổi (nếu có)
            if dto.conversion_unit_id is not None:
                conversion = UnitConversion(
                    id=None,
                    product_id=product_id,
                    from_unit_id=dto.base_unit_id,
                    to_unit_id=dto.conversion_unit_id,
                    ratio=dto.conversion_ratio
                )
                unit_conv_repo.create_unit_conversion(conversion)

            transaction.commit()
            return product_id

        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()

    # =========================
    # UPDATE
    # =========================

    def update_product(self, dto: ProductUpdateDTO) -> bool:
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            product_repo = ProductRepositoryImpl(connection)
            unit_conv_repo = UnitConversionRepositoryImpl(connection)
            validator = ProductValidator(product_repo)

            validator.validate_update(dto)
            product = ProductMapper.to_entity_from_update_dto(dto)

            updated = product_repo.update_product(product)

            if dto.conversion_unit_id is not None:
                conversion = UnitConversion(
                    id=None,
                    product_id=dto.product_id,
                    from_unit_id=dto.base_unit_id,
                    to_unit_id=dto.conversion_unit_id,
                    ratio=dto.conversion_ratio
                )

                # Cần kiểm tra xem trước đó đã có quy đổi chưa để Insert hay Update
                existing_conv = unit_conv_repo.get_unit_conversion(dto.product_id)
                if existing_conv:
                    unit_conv_repo.update_unit_conversion(conversion)
                else:
                    unit_conv_repo.create_unit_conversion(conversion)

            transaction.commit()
            return updated

        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()

    # =========================
    # DELETE
    # =========================

    def delete_product(self, dto: ProductDeleteDTO) -> bool:
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            product_repo = ProductRepositoryImpl(connection)
            inventory_repo = InventoryRepositoryImpl(connection)

            validator = ProductValidator(
                product_repository=product_repo,
                inventory_repository=inventory_repo
            )

            # Hàm này giờ sẽ chạy hoàn hảo!
            validator.validate_delete(dto)

            deleted = product_repo.soft_delete_product(dto.product_id)

            transaction.commit()
            return deleted

        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()

    def get_product_sale_list(self, keyword: str = None) -> list:
        connection = DatabaseConnection.get_connection()
        try:
            product_repo = ProductRepositoryImpl(connection)
            return product_repo.get_product_sale_list(keyword)
        except Exception as e:
            print(f"Lỗi khi lấy danh sách sản phẩm POS: {e}")
            raise
        finally:
            connection.close()

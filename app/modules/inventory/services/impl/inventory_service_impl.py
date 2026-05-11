import time
from typing import List

from app.core.database.connection import DatabaseConnection
from app.core.database.transaction import TransactionManager  # THÊM DÒNG NÀY
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, InventoryListDTO
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO

from app.modules.inventory.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl
from app.modules.product.repositories.impl.product_repository_impl import ProductRepositoryImpl
from app.modules.product.repositories.impl.supplier_repository_impl import SupplierRepositoryImpl
from app.modules.inventory.validators.inventory_validator import InventoryValidator


class InventoryServiceImpl(InventoryService):
    def __init__(self):
        # Service giờ hoàn toàn độc lập, không cần truyền Repo từ ngoài vào
        pass

    def get_inventory_list(self, search_keyword: str = None) -> List[InventoryListDTO]:
        # Khởi tạo connection mới -> Giải quyết triệt để lỗi "Bóng ma dữ liệu"
        connection = DatabaseConnection.get_connection()
        try:
            inventory_repo = InventoryRepositoryImpl(connection)
            raw_data = inventory_repo.get_inventory_list_data(search_keyword)
            result = []

            for row in raw_data:
                total_qty = int(row['total_base_quantity']) if row['total_base_quantity'] else 0
                min_stock = int(row['min_stock']) if row['min_stock'] else 0
                ratio = row['conversion_ratio']
                conv_name = row['conversion_unit_name']
                base_name = row['base_unit_name']

                conv_str = "---"
                if ratio and conv_name and ratio > 0:
                    ratio_int = int(ratio)
                    si_qty = total_qty // ratio_int
                    le_qty = total_qty % ratio_int

                    if si_qty > 0 and le_qty > 0:
                        conv_str = f"{si_qty} {conv_name} + {le_qty} {base_name}"
                    elif si_qty > 0 and le_qty == 0:
                        conv_str = f"{si_qty} {conv_name}"
                    else:
                        conv_str = f"{le_qty} {base_name}"

                status = "Sắp hết hàng" if total_qty <= min_stock else "Bình thường"

                dto = InventoryListDTO(
                    product_id=row['product_id'],
                    sku=row['sku'],
                    product_name=row['product_name'],
                    base_unit_name=base_name,
                    total_base_quantity=total_qty,
                    conversion_quantity_str=conv_str,
                    min_stock=min_stock,
                    status=status
                )
                result.append(dto)

            return result
        finally:
            connection.close()

    def create_purchase_order(self, dto: PurchaseOrderCreateDTO) -> int:
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            # Bơm connection vào các repo, tự động chia sẻ cùng 1 Transaction
            inventory_repo = InventoryRepositoryImpl(connection)
            product_repo = ProductRepositoryImpl(connection)
            supplier_repo = SupplierRepositoryImpl(connection)

            validator = InventoryValidator(product_repo, supplier_repo)

            # Validation chạy trên cùng connection, KHÔNG CẦN TRUYỀN CURSOR
            validator.validate_purchase_order(dto)

            total_amount = sum(item.quantity * item.unit_price for item in dto.items)
            po_code = f"PN-{int(time.time())}"

            # Gọi Repo, KHÔNG CẦN TRUYỀN CURSOR
            po_id = inventory_repo.create_purchase_order({
                'code': po_code,
                'supplier_id': dto.supplier_id,
                'total_amount': total_amount,
                'note': dto.note
            })

            for item in dto.items:
                product = product_repo.get_product_by_id(item.product_id)

                base_qty = item.quantity
                conv_unit_id = getattr(product, 'conversion_unit_id', None)
                conv_ratio = getattr(product, 'conversion_ratio', None)

                if conv_unit_id and item.unit_id == conv_unit_id and conv_ratio:
                    base_qty = item.quantity * int(conv_ratio)

                inventory_repo.create_purchase_order_item({
                    'po_id': po_id, 'product_id': item.product_id, 'unit_id': item.unit_id,
                    'qty': item.quantity, 'price': item.unit_price, 'total': item.quantity * item.unit_price
                })

                inventory_repo.add_stock_transaction({
                    'product_id': item.product_id, 'qty': base_qty, 'ref_id': po_id
                })

                inventory_repo.update_inventory_quantity(item.product_id, base_qty)

            transaction.commit()
            return po_id

        except Exception as e:
            transaction.rollback()
            raise Exception(f"Lỗi hệ thống khi lưu phiếu nhập: {str(e)}")
        finally:
            connection.close()

    def search_products_for_import(self, keyword: str) -> List[ProductDetailDTO]:
        connection = DatabaseConnection.get_connection()
        try:
            product_repo = ProductRepositoryImpl(connection)
            results = []
            if not keyword:
                return results

            search_list = product_repo.search_products(
                keyword=keyword, category_id=None, supplier_id=None, is_active=True
            )

            for item in search_list:
                prod_id = item.get('id')
                if prod_id:
                    raw_data = product_repo.get_product_detail_for_import(prod_id)

                    if raw_data:
                        dto = self._map_raw_to_dto(raw_data)
                        results.append(dto)

            return results
        finally:
            connection.close()

    def _map_raw_to_dto(self, data: dict) -> ProductDetailDTO:
        return ProductDetailDTO(
            id=data.get('id', 0),
            sku=data.get('sku', ''),
            name=data.get('name', ''),
            barcode=data.get('barcode', ''),
            category_id=data.get('category_id'),
            category_name=data.get('category_name', ''),
            supplier_id=data.get('supplier_id'),
            supplier_name=data.get('supplier_name', ''),
            base_unit_id=data.get('base_unit_id'),
            base_unit_name=data.get('base_unit_name', 'Cơ bản'),
            cost_price=data.get('cost_price', 0),
            retail_price=data.get('retail_price', 0),
            wholesale_price=data.get('wholesale_price', 0),
            min_stock=data.get('min_stock', 0),
            conversion_unit_id=data.get('conversion_unit_id'),
            conversion_unit_name=data.get('conversion_unit_name', 'Quy đổi'),
            conversion_ratio=data.get('conversion_ratio'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
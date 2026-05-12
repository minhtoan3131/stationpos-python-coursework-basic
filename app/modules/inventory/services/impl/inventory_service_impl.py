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
            inventory_repo = InventoryRepositoryImpl(connection)
            product_repo = ProductRepositoryImpl(connection)
            supplier_repo = SupplierRepositoryImpl(connection)

            validator = InventoryValidator(product_repo, supplier_repo)

            validator.validate_purchase_order(dto)

            total_amount = sum(item.quantity * item.unit_price for item in dto.items)
            po_code = f"PN-{int(time.time())}"

            po_id = inventory_repo.create_purchase_order({
                'code': po_code,
                'supplier_id': dto.supplier_id,
                'total_amount': total_amount,
                'note': dto.note
            })

            for item in dto.items:
                # 1. Lấy thông tin sản phẩm (Chứa Tỷ lệ quy đổi & Giá vốn cũ)
                product_data = product_repo.get_product_detail_for_import(item.product_id)
                old_cost_price = float(product_data.get('cost_price') or 0)

                # Lấy số lượng tồn kho CŨ (trước khi cộng lô mới)
                current_qty = inventory_repo.get_inventory_quantity(item.product_id)

                base_qty = item.quantity
                conv_unit_id = product_data.get('conversion_unit_id')
                conv_ratio = product_data.get('conversion_ratio')

                # 2. Quy đổi Số lượng & Giá nhập ra ĐƠN VỊ CƠ BẢN
                if conv_unit_id and item.unit_id == conv_unit_id and conv_ratio:
                    ratio_val = float(conv_ratio)
                    # Nhập Sỉ -> Nhân SL với Tỷ lệ
                    base_qty = item.quantity * int(ratio_val)
                    # Nhập Sỉ -> Chia Giá nhập cho Tỷ lệ để ra Giá Cơ bản
                    base_unit_cost = float(item.unit_price) / ratio_val
                else:
                    # Nhập Lẻ -> Giữ nguyên SL và Giá
                    base_unit_cost = float(item.unit_price)

                # 3. Tính GIÁ VỐN BÌNH QUÂN GIA QUYỀN (MAC)
                total_new_qty = current_qty + base_qty

                if total_new_qty > 0:
                    old_total_value = current_qty * old_cost_price
                    new_total_value = base_qty * base_unit_cost

                    # Công thức MAC = Tổng giá trị / Tổng số lượng
                    new_mac = (old_total_value + new_total_value) / total_new_qty
                else:
                    # Đề phòng trường hợp lỗi kho âm, lấy luôn giá mới làm chuẩn
                    new_mac = base_unit_cost

                # 4. Lưu Giá vốn bình quân MỚI vào bảng Sản phẩm
                product_repo.update_cost_price(item.product_id, new_mac)

                # 5. Lưu Chi tiết phiếu nhập (Lưu nguyên trạng ĐVT và Giá mà Thu ngân đã nhập)
                inventory_repo.create_purchase_order_item({
                    'po_id': po_id, 'product_id': item.product_id, 'unit_id': item.unit_id,
                    'qty': item.quantity, 'price': item.unit_price, 'total': item.quantity * item.unit_price
                })

                # 6. Ghi nhận lịch sử (Thẻ kho) theo SL Cơ bản
                inventory_repo.add_stock_transaction({
                    'product_id': item.product_id, 'qty': base_qty, 'ref_id': po_id
                })

                # 7. Cộng tồn kho theo SL Cơ bản
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
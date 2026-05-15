import time
from decimal import Decimal
from typing import List, Callable

from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, InventoryListDTO
from app.modules.inventory.utils.inventory_excel_exporter import InventoryExcelExporter
from app.modules.inventory.utils.mac_calculator import MACCalculator
from app.modules.inventory.utils.unit_converter import UnitConverter
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO
from app.modules.inventory.validators.inventory_validator import InventoryValidator
from app.core.exceptions.validation_exception import ValidationException


class InventoryServiceImpl(InventoryService):

    def __init__(self, uow_factory: Callable):
        """
        uow_factory: Truyền chính class UnitOfWork vào đây.
        Mỗi khi gọi self.uow_factory(), nó sẽ sinh ra 1 phiên kết nối mới.
        """
        self.uow_factory = uow_factory

    # ==========================================
    # DANH SÁCH TỒN KHO
    # ==========================================
    def get_inventory_list(self, search_keyword: str = None) -> List[InventoryListDTO]:
        with self.uow_factory() as db:
            raw_data = db.inventory_repo.get_inventory_list_data(search_keyword)
            result = []

            for row in raw_data:
                total_qty = int(row['total_base_quantity']) if row['total_base_quantity'] else 0
                min_stock = int(row['min_stock']) if row['min_stock'] else 0

                conv_str = UnitConverter.format_conversion_string(
                    total_qty=total_qty,
                    ratio=row['conversion_ratio'],
                    conv_name=row['conversion_unit_name'],
                    base_name=row['base_unit_name']
                )

                result.append(InventoryListDTO(
                    product_id=row['product_id'],
                    sku=row['sku'],
                    product_name=row['product_name'],
                    base_unit_name=row['base_unit_name'],
                    total_base_quantity=total_qty,
                    conversion_quantity_str=conv_str,
                    min_stock=min_stock,
                    is_low_stock=(total_qty <= min_stock)
                ))
            return result

    # ==========================================
    # LƯU PHIẾU NHẬP KHO (TRANSACTION PHỨC TẠP)
    # ==========================================
    def create_purchase_order(self, dto: PurchaseOrderCreateDTO) -> int:
        try:
            # Khởi tạo UnitOfWork. Nếu code trong 'with' chạy thành công, tự động Commit.
            # Nếu có lỗi (Exception), tự động Rollback.
            with self.uow_factory() as db:

                # 1. Validate
                validator = InventoryValidator(db.product_repo, db.supplier_repo)
                validator.validate_purchase_order(dto)

                # 2. Tạo phiếu nhập cha
                total_amount = sum(item.quantity * item.unit_price for item in dto.items)
                po_code = f"PN-{int(time.time())}"

                po_id = db.inventory_repo.create_purchase_order({
                    'code': po_code,
                    'supplier_id': dto.supplier_id,
                    'total_amount': total_amount,
                    'note': dto.note
                })

                # 3. Duyệt từng mặt hàng nhập
                for item in dto.items:
                    product_data = db.product_repo.get_product_detail_for_import(item.product_id)
                    inv_status = db.inventory_repo.get_inventory_status(item.product_id)

                    current_qty = inv_status['quantity']
                    current_total_val = Decimal(str(inv_status['total_value']))

                    base_qty = item.quantity
                    conv_unit_id = product_data.get('conversion_unit_id')
                    conv_ratio = product_data.get('conversion_ratio')

                    if conv_unit_id and item.unit_id == conv_unit_id and conv_ratio:
                        base_qty = item.quantity * int(float(conv_ratio))

                    import_total_val = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))

                    # 4. Tính MAC thuần túy
                    new_qty, new_total_val, new_mac = MACCalculator.calculate_standard_mac(
                        current_qty=current_qty,
                        current_total_value=current_total_val,
                        import_qty=base_qty,
                        import_total_value=import_total_val
                    )

                    # 5. Cập nhật qua Repo
                    db.product_repo.update_cost_price(item.product_id, new_mac)
                    db.inventory_repo.update_inventory_status(item.product_id, new_qty, new_total_val)
                    db.inventory_repo.create_purchase_order_item({
                        'po_id': po_id, 'product_id': item.product_id, 'unit_id': item.unit_id,
                        'qty': item.quantity, 'price': item.unit_price, 'total': item.quantity * item.unit_price
                    })
                    db.inventory_repo.add_stock_transaction({
                        'product_id': item.product_id, 'qty': base_qty, 'ref_id': po_id
                    })

                return po_id

        except ValidationException:
            raise  # Bắn lỗi Validation lên UI trực tiếp
        except Exception as e:
            raise Exception(f"Lỗi hệ thống khi lưu phiếu nhập: {str(e)}")

    # ==========================================
    # CÁC HÀM KHÁC
    # ==========================================
    def search_products_for_import(self, keyword: str) -> List[ProductDetailDTO]:
        if not keyword: return []

        with self.uow_factory() as db:
            results = []
            search_list = db.product_repo.search_products(
                keyword=keyword, category_id=None, supplier_id=None, is_active=True
            )

            for item in search_list:
                prod_id = item.get('id')
                if prod_id:
                    raw_data = db.product_repo.get_product_detail_for_import(prod_id)
                    if raw_data:
                        results.append(self._map_raw_to_dto(raw_data))

            return results

    def export_inventory_to_excel(self, file_path: str) -> bool:
        with self.uow_factory() as db:
            data = db.inventory_repo.get_inventory_report_data()
            return InventoryExcelExporter.export(data, file_path)

    # Mapper nội bộ
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
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
    # LƯU PHIẾU NHẬP KHO
    # ==========================================
    def create_purchase_order(self, dto: PurchaseOrderCreateDTO) -> int:


        with self.uow_factory() as db:
            # KHỞI TẠO VALIDATOR VÀ TRUYỀN REPO TỪ BIẾN DB XUỐNG
            validator = InventoryValidator(
                product_repo=db.product_repo,
                supplier_repo=db.supplier_repo
            )
            # Tiến hành Validate trước khi chạy logic nghiệp vụ chính
            validator.validate_purchase_order(dto)
            # Tạo mã hóa đơn dựa trên timestamp
            po_code = f"PO-{int(time.time())}"

            # Tính toán tổng giá trị hóa đơn (Line Total) để lưu Master Header
            total_amount = 0
            calculated_items = []

            for item in dto.items:
                # Tìm kiếm thông tin chuyển đổi đơn vị tính từ DB
                conv = db.inventory_repo.get_conversion_info(item.product_id, item.unit_id)
                ratio = Decimal(str(conv['ratio'])) if conv else Decimal('1')

                # Tính quy đổi số lượng về đơn vị cơ bản và tổng tiền thực trả của dòng
                base_qty = item.quantity * int(ratio)
                import_total_val = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
                total_amount += float(import_total_val)

                calculated_items.append((item, base_qty, import_total_val))

            # Bước 2: Tạo bản ghi Master Phiếu Nhập
            po_id = db.inventory_repo.create_purchase_order({
                'code': po_code,
                'supplier_id': dto.supplier_id,
                'total_amount': total_amount,
                'note': dto.note
            })

            # Bước 3 & 4: Vòng lặp xử lý chi tiết kho và định giá thông minh
            for item, base_qty, import_total_val in calculated_items:
                # Truy vấn trạng thái kho hiện tại và Khóa dòng (FOR UPDATE)
                current_stock = db.inventory_repo.get_inventory_status(item.product_id)
                current_qty = current_stock['quantity']
                current_total_val = Decimal(str(current_stock['total_value']))

                try:
                    # Đẩy vào bộ máy tính toán MAC thông minh
                    new_qty, new_total_val, new_mac, garbage_value = MACCalculator.calculate_standard_mac(
                        current_qty=current_qty,
                        current_total_value=current_total_val,
                        import_qty=base_qty,
                        import_total_value=import_total_val
                    )

                    # TRƯỜNG HỢP A: Nếu phát hiện có rác tài chính (Lệch làm tròn trước đó), ghi nhận log điều chỉnh dữ liệu ngoại vi
                    if garbage_value is not None:
                        db.inventory_repo.add_stock_transaction({
                            'product_id': item.product_id,
                            'qty': 0,  # Biến động vật lý bằng 0 vì chỉ xử lý rác tiền
                            'type': 'DATA_CORRECTION',  # Ghi nhận log dọn rác kế toán
                            'variance_amount': -garbage_value,  # Số tiền âm để triệt tiêu rác
                            'note': "Điều chỉnh dọn rác giá trị tồn đọng khi kho trống",  # Văn bản bắt buộc
                            'ref_id': po_id
                        })

                    # Cập nhật thông số giá vốn mới vào danh mục sản phẩm
                    db.product_repo.update_cost_price(item.product_id, new_mac)

                    # Cập nhật số lượng và tổng giá trị tồn kho mới vào két sắt hệ thống
                    db.inventory_repo.update_inventory_status(item.product_id, new_qty, new_total_val)

                    # Lưu lịch sử chi tiết mặt hàng thuộc Phiếu nhập
                    db.inventory_repo.create_purchase_order_item({
                        'purchase_order_id': po_id,
                        'product_id': item.product_id,
                        'unit_id': item.unit_id,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'total_price': float(import_total_val)
                    })

                    # Log dòng dịch chuyển vật lý thông thường (IMPORT)
                    db.inventory_repo.add_stock_transaction({
                        'product_id': item.product_id,
                        'qty': base_qty,
                        'type': 'IMPORT',
                        'ref_id': po_id
                    })

                except ValueError as ve:
                    # Bắt lỗi từ chốt chặn kho âm của MACCalculator để đẩy lên UI cảnh báo
                    error_key = str(ve)
                    if error_key in ["KHO_AM_CHAN_NGHIEP_VU", "NHAP_KHO_VAN_AM_CHAN_NGHIEP_VU"]:
                        raise ValidationException(
                            f"Hệ thống đã dừng nghiệp vụ nhập kho cho Sản phẩm ID {item.product_id}. "
                            f"Phát hiện trạng thái kho âm bất hợp lệ (Mô hình bán khống chưa được kích hoạt)."
                        )
                    raise ve

            return po_id
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
from typing import Callable, List
from decimal import Decimal

from app.modules.inventory.services.po_history_service import PurchaseOrderHistoryService
from app.modules.inventory.dtos.po_history_dto import (
    PurchaseOrderHistoryFilterDTO,
    PurchaseOrderMasterDTO,
    PurchaseOrderDetailDTO
)
from app.core.exceptions.validation_exception import ValidationException


class PurchaseOrderHistoryServiceImpl(PurchaseOrderHistoryService):

    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    def search_history(self, filter_dto: PurchaseOrderHistoryFilterDTO) -> List[PurchaseOrderMasterDTO]:
        with self.uow_factory() as db:
            raw_data = db.po_history_repo.search_purchase_orders(
                from_date=filter_dto.from_date,
                to_date=filter_dto.to_date,
                keyword=filter_dto.keyword,
                status=filter_dto.status
            )

            # Map dữ liệu thô từ Database sang DTO
            result = []
            for row in raw_data:
                result.append(PurchaseOrderMasterDTO(
                    id=row['id'],
                    code=row['code'],
                    created_at=row['created_at'],
                    supplier_name=row['supplier_name'],
                    total_amount=float(row['total_amount']),
                    status=row['status'],
                    note=row['note'],
                    cancel_reason=row['cancel_reason']
                ))
            return result

    def get_details(self, po_id: int) -> List[PurchaseOrderDetailDTO]:
        with self.uow_factory() as db:
            raw_data = db.po_history_repo.get_purchase_order_items(po_id)

            result = []
            for row in raw_data:
                result.append(PurchaseOrderDetailDTO(
                    product_id=row['product_id'],
                    sku=row['sku'],
                    product_name=row['product_name'],
                    unit_name=row['unit_name'],
                    quantity=row['quantity'],
                    unit_price=float(row['unit_price']),
                    total_price=float(row['total_price'])
                ))
            return result

    def cancel_purchase_order(self, po_id: int, cancel_reason: str) -> None:
        if not cancel_reason or not cancel_reason.strip():
            raise ValidationException("Vui lòng nhập lý do hủy phiếu.")

        try:
            with self.uow_factory() as db:
                # Lấy thông tin phiếu và kiểm tra trạng thái
                po_master = db.po_history_repo.get_purchase_order_by_id(po_id)
                if not po_master:
                    raise ValidationException("Không tìm thấy phiếu nhập này.")

                if po_master['status'] == 'CANCELLED':
                    raise ValidationException("Phiếu nhập này đã được hủy trước đó.")

                # Lấy danh sách mặt hàng để kiểm tra và trừ kho
                po_items = db.po_history_repo.get_purchase_order_items(po_id)

                for item in po_items:
                    product_id = item['product_id']
                    imported_qty = item['quantity']
                    imported_unit_id = item['unit_id']  # Lấy unit_id lúc nhập
                    imported_total_price = Decimal(str(item['total_price']))

                    # Lấy thông tin quy đổi của sản phẩm
                    product_data = db.product_repo.get_product_detail_for_import(product_id)

                    base_qty_to_deduct = imported_qty
                    conv_unit_id = product_data.get('conversion_unit_id')
                    conv_ratio = product_data.get('conversion_ratio')

                    # KIỂM TRA QUY ĐỔI: Nếu đơn vị lúc nhập chính là đơn vị quy đổi (Ví dụ: Thùng)
                    if conv_unit_id and imported_unit_id == conv_unit_id and conv_ratio:
                        # Ép ratio về int/float giống hệt cách làm ở hàm create_purchase_order
                        base_qty_to_deduct = imported_qty * int(float(conv_ratio))

                    # Tiếp tục logic lấy kho hiện tại và trừ kho
                    inv_status = db.inventory_repo.get_inventory_status(product_id)
                    current_qty = inv_status['quantity']
                    current_total_value = Decimal(str(inv_status['total_value']))

                    # NGHIỆP VỤ LÕI: Kho không đủ thì cấm hủy
                    if current_qty < base_qty_to_deduct:
                        raise ValidationException(
                            f"Sản phẩm [{item['sku']}] không đủ số lượng tồn để hủy. "
                            f"(Tồn: {current_qty}, Cần trừ: {base_qty_to_deduct})"
                        )

                    # ==========================================
                    # TÍNH TOÁN LẠI TỒN KHO & MAC
                    # ==========================================
                    new_qty = current_qty - base_qty_to_deduct
                    new_total_value = current_total_value - imported_total_price
                    new_mac = Decimal('0')

                    if new_qty == 0:
                        # CHỐT CHẶN 0: Nếu kho cạn sạch, ép tổng giá trị về 0 VNĐ
                        # Mọi sai số (nếu có) sẽ tự động bị loại bỏ
                        new_total_value = Decimal('0')
                        new_mac = Decimal('0')
                    else:
                        # Nếu kho vẫn còn hàng, tính lại MAC lùi
                        new_mac = new_total_value / Decimal(str(new_qty))

                    # ==========================================
                    # THỰC THI UPDATE VÀO DATABASE
                    # ==========================================
                    # Cập nhật Kho (inventory)
                    db.inventory_repo.update_inventory_status(product_id, new_qty, new_total_value)

                    # Cập nhật Giá vốn MAC (products)
                    db.product_repo.update_cost_price(product_id, new_mac)

                    # Ghi Log Hủy (stock_transactions)
                    db.inventory_repo.add_stock_transaction({
                        'product_id': product_id,
                        'qty': -base_qty_to_deduct,  # Dấu âm thể hiện xuất/trừ đi
                        'type': 'CANCEL',
                        'ref_id': po_id
                    })

                # Cập nhật trạng thái phiếu nhập
                db.po_history_repo.update_purchase_order_status(po_id, 'CANCELLED', cancel_reason)


        except ValidationException:
            raise
        except Exception as e:
            raise Exception(f"Lỗi hệ thống khi hủy phiếu nhập: {str(e)}")
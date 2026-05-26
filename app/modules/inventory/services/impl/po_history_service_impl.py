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

        with self.uow_factory() as db:
            # Lấy thông tin phiếu nhập Master Header
            po_master = db.po_history_repo.get_purchase_order_by_id(po_id)
            if not po_master:
                raise ValidationException("Không tìm thấy phiếu nhập này.")

            if po_master['status'] == 'CANCELLED':
                raise ValidationException("Phiếu nhập này đã được hủy trước đó.")

            # Lấy danh sách mặt hàng chi tiết thuộc phiếu nhập để kiểm tra
            po_items = db.po_history_repo.get_purchase_order_items(po_id)
            po_timestamp = po_master['created_at']  # Timestamp của phiếu nhập phục vụ Chốt chặn 2

            # Bước 1: Vòng lặp Validation chốt chặn kép trước khi biến động bất kỳ dòng dữ liệu nào
            for item in po_items:
                product_id = item['product_id']
                imported_qty = item['quantity']
                imported_unit_id = item['unit_id']

                # Tính toán số lượng quy đổi cơ bản
                product_data = db.product_repo.get_product_detail_for_import(product_id)
                base_qty_to_deduct = imported_qty
                conv_unit_id = product_data.get('conversion_unit_id')
                conv_ratio = product_data.get('conversion_ratio')

                if conv_unit_id and imported_unit_id == conv_unit_id and conv_ratio:
                    base_qty_to_deduct = imported_qty * int(float(conv_ratio))

                # --- CHỐT CHẶN 2: Bảo vệ Lịch sử MAC (QUAN TRỌNG) ---
                if db.po_history_repo.has_subsequent_delivery_transactions(product_id, po_timestamp):
                    raise ValidationException(
                        f"Hàng hóa thuộc sản phẩm [{item['sku']}] đã bị xuất bán hoặc điều chuyển "
                        f"sau thời điểm nhập phiếu này. Vui lòng sử dụng nghiệp vụ Trả hàng NCC."
                    )

                # --- CHỐT CHẶN 1: Logic Tồn kho (Khóa dòng FOR UPDATE qua get_inventory_status) ---
                inv_status = db.inventory_repo.get_inventory_status(product_id)
                current_qty = inv_status['quantity']

                if current_qty < base_qty_to_deduct:
                    raise ValidationException(
                        f"Hủy phiếu nhập sẽ làm kho bị âm, vi phạm chính sách! "
                        f"Sản phẩm [{item['sku']}] không đủ lượng tồn. (Tồn hiện tại: {current_qty}, Cần trừ: {base_qty_to_deduct})"
                    )

            # Bước 2 & 3 & 4: Thực thi biến động dữ liệu khi các chốt chặn đã an toàn vượt qua
            for item in po_items:
                product_id = item['product_id']
                imported_qty = item['quantity']
                imported_unit_id = item['unit_id']
                imported_total_price = Decimal(str(item['total_price']))

                product_data = db.product_repo.get_product_detail_for_import(product_id)
                base_qty_to_deduct = imported_qty
                if product_data.get('conversion_unit_id') and imported_unit_id == product_data.get(
                        'conversion_unit_id') and product_data.get('conversion_ratio'):
                    base_qty_to_deduct = imported_qty * int(float(product_data.get('conversion_ratio')))

                inv_status = db.inventory_repo.get_inventory_status(product_id)
                current_qty = inv_status['quantity']
                current_total_value = Decimal(str(inv_status['total_value']))

                # Tiến hành rút lùi toán học
                new_qty = current_qty - base_qty_to_deduct
                new_total_value_tmp = current_total_value - imported_total_price
                new_total_value = new_total_value_tmp

                # --- CHỐT CHẶN MINH BẠCH: Dọn rác thập phân lúc nhập (Trường hợp kho về 0 nhưng còn đọng tiền rác) ---
                if new_qty == 0 and new_total_value_tmp != 0:
                    variance = new_total_value_tmp

                    # Bắn log hạch toán ADJUST_VARIANCE để giải trình chênh lệch kế toán ngoại vi
                    db.inventory_repo.add_stock_transaction({
                        'product_id': product_id,
                        'qty': 0,
                        'type': 'ADJUST_VARIANCE',
                        'variance_amount': variance,
                        'note': f"Hủy phiếu: Điều chỉnh dọn rác giá trị tồn đọng khi kho trống",
                        'ref_id': po_id
                    })
                    # Ép môi trường sạch tuyệt đối về 0đ
                    new_total_value = Decimal('0')

                # Tính toán lại chỉ số MAC lùi sau khi rút hàng
                if new_qty > 0:
                    new_mac = new_total_value / Decimal(str(new_qty))
                    # Đảm bảo làm tròn nửa lên 4 chữ số thập phân lưu trữ DB
                    new_mac = new_mac.quantize(Decimal('0.0001'))
                    new_total_value = new_total_value.quantize(Decimal('0.0001'))
                else:
                    new_mac = Decimal('0.0000')
                    new_total_value = Decimal('0.0000')

                # Cập nhật số dư két sắt tồn kho mới
                db.inventory_repo.update_inventory_status(product_id, new_qty, new_total_value)

                # Ghi nhận lại giá vốn hàng hóa lùi lịch sử vào danh mục sản phẩm
                db.product_repo.update_cost_price(product_id, new_mac)

                # Ghi nhận log dịch chuyển kho vật lý tiêu chuẩn (CANCEL) mang số lượng Âm
                db.inventory_repo.add_stock_transaction({
                    'product_id': product_id,
                    'qty': -base_qty_to_deduct,
                    'type': 'CANCEL',
                    'variance_amount': Decimal('0.0000'),
                    'note': f"Hủy phiếu nhập hệ thống: {po_master['code']}",
                    'ref_id': po_id
                })

            # Bước 2: Cập nhật Master Header của Phiếu nhập sang trạng thái hủy và ghi lý do
            db.po_history_repo.update_purchase_order_status(po_id, 'CANCELLED', cancel_reason)
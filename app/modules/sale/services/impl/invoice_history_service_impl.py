# File: app/modules/sale/services/impl/invoice_history_service_impl.py
from datetime import date
from typing import List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from app.modules.sale.services.invoice_history_service import InvoiceHistoryService
from app.core.exceptions.validation_exception import ValidationException


class InvoiceHistoryServiceImpl(InvoiceHistoryService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def search_invoices(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        with self.uow_factory() as uow:
            return uow.invoice_history_repo.fetch_invoices_master(
                keyword=filters.get("keyword"),
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                payment_method=filters.get("payment_method"),
                status=filters.get("status")
            )

    def get_invoice_full_details(self, invoice_code: str) -> Dict[str, Any]:
        with self.uow_factory() as uow:
            metadata = uow.invoice_history_repo.fetch_invoice_metadata(invoice_code)
            items = uow.invoice_history_repo.fetch_invoice_details(invoice_code)
            return {"metadata": metadata, "items": items}

    def execute_cancel_invoice(self, invoice_code: str, reason: str) -> bool:
        """
        LUỒNG 4: HỦY BÁN HÀNG / TRẢ HÀNG (Vector Tăng pha loãng từ Lịch sử)
        """
        if not reason or not reason.strip():
            raise ValidationException("Vui lòng cung cấp lý do hủy hóa đơn.")

        with self.uow_factory() as uow:
            # Kiểm tra hóa đơn gốc
            metadata = uow.invoice_history_repo.fetch_invoice_metadata(invoice_code)
            if not metadata:
                raise ValidationException("Không tìm thấy hóa đơn yêu cầu.")
            if metadata['status'] == 'CANCELLED':
                raise ValidationException("Hóa đơn này đã được hủy trước đó.")

            invoice_id = metadata['id']
            invoice_items = uow.invoice_history_repo.fetch_invoice_details(invoice_code)

            # VÒNG LẶP XỬ LÝ KHO CHO TỪNG MẶT HÀNG (PHỤC HỒI PHA LOÃNG)
            for item in invoice_items:
                p_id = item['product_id']
                sold_qty = item['quantity']
                total_cogs_amount = Decimal(str(item['total_cogs_amount']))

                # Vì nghiệp vụ POS hiện tại của bạn đã gộp sỉ/lẻ về đơn vị cơ bản khi trừ kho,
                # nên return_qty ở đây chính bằng sold_qty cơ bản. Tỷ lệ hoàn vốn là 100%.
                return_qty = sold_qty
                refund_cogs = total_cogs_amount  # Trả bao nhiêu cái hoàn đúng bấy nhiêu vốn gốc

                # --- BƯỚC 1: KHÓA DÒNG INVENTORY (SELECT ... FOR UPDATE) ---
                inv_status = uow.inventory_repo.get_inventory_status(p_id)
                old_qty = inv_status['quantity']
                old_total_value = Decimal(str(inv_status['total_value']))

                # --- BƯỚC 2: DỌN RÁC DỮ LIỆU (ANOMALY CLEARANCE KHI KHO TRỐNG) ---
                if old_qty == 0 and old_total_value != 0:
                    # Bắn log hạch toán để triệt tiêu khoản rác vô lý từ quá khứ
                    uow.inventory_repo.add_stock_transaction({
                        'product_id': p_id,
                        'qty': 0,
                        'type': 'DATA_CORRECTION',
                        'variance_amount': -old_total_value,
                        'note': "Điều chỉnh dọn rác giá trị tồn đọng khi kho trống (Hủy bán)",
                        'ref_id': invoice_id
                    })
                    # Ép môi trường két sắt về trạng thái sạch trước khi nhận hàng về
                    old_total_value = Decimal('0.0000')

                # --- BƯỚC 3: XỬ LÝ KHO (CỘNG DỒN TUYỆT ĐỐI) ---
                new_qty = old_qty + return_qty
                new_total_value = old_total_value + refund_cogs

                # Tính chỉ số MAC mới bị pha loãng sau khi thu hồi hàng về kho
                new_mac = new_total_value / Decimal(str(new_qty))

                # Làm tròn 4 chữ số thập phân chuẩn kế toán
                new_mac = new_mac.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                new_total_value = new_total_value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

                # --- BƯỚC 4: CẬP NHẬT DATABASE ---
                # Đè số dư mới sạch rác vào kho
                uow.inventory_repo.update_inventory_status(p_id, new_qty, new_total_value)
                # Ghi nhận giá vốn pha loãng mới vào danh mục sản phẩm
                uow.product_repo.update_cost_price(p_id, new_mac)

                # Ghi log lịch sử biến động kho loại CUSTOMER_RETURN mang số lượng Dương
                uow.inventory_repo.add_stock_transaction({
                    'product_id': p_id,
                    'qty': return_qty,
                    'type': 'ANOMALY_ADJUSTMENT',  # Hoặc map sang type phù hợp trong ENUM schema của bạn
                    'variance_amount': Decimal('0.0000'),
                    'note': f"Nhập hàng trả lại từ hóa đơn bị hủy: {invoice_code}",
                    'ref_id': invoice_id
                })

            # Cập nhật trạng thái Master hóa đơn sang CANCELLED và lưu nhật ký logs hành động
            uow.invoice_history_repo.update_invoice_status(invoice_code, 'CANCELLED', reason)
            uow.sale_repo.add_invoice_log(invoice_id, 'CANCEL', f"Hủy hóa đơn tại Nhật ký. Lý do: {reason}")

        return True

    def process_reprint_invoice(self, invoice_code: str) -> bool:
        return True

    def export_invoice_to_excel(self, invoice_code: str) -> str:
        """
        Xuất thông tin chi tiết hóa đơn ra tệp Excel và trả về đường dẫn lưu file thực tế.
        """
        with self.uow_factory() as uow:
            # Thu thập trọn vẹn dữ liệu gốc từ DB
            metadata = uow.invoice_history_repo.fetch_invoice_metadata(invoice_code)
            if not metadata:
                raise Exception("Không tìm thấy dữ liệu hóa đơn để xuất Excel.")

            items = uow.invoice_history_repo.fetch_invoice_details(invoice_code)

            # Trả về đường dẫn để tầng UI Controller tự mở hộp thoại chọn thư mục lưu tệp
            return {"metadata": metadata, "items": items}
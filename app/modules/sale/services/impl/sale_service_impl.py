from decimal import Decimal

from app.core.database.unit_of_work import UnitOfWork
from app.core.exceptions.validation_exception import ValidationException
from app.modules.sale.dtos.sale_dto import CheckoutDTO
from app.modules.sale.services.sale_service import SaleService
from app.modules.sale.utils.invoice_code_generator import InvoiceCodeGenerator
from app.modules.sale.validators.sale_validator import SaleValidator


class SaleServiceImpl(SaleService):

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def process_checkout(self, checkout_data: CheckoutDTO) -> str:
        """
        Hàm điều phối luồng thanh toán chính.
        """
        SaleValidator.validate_checkout_data(checkout_data)

        with self.uow_factory() as uow:
            # Chuẩn bị dữ liệu trừ kho và Validate tồn kho
            product_deduction_map = self._prepare_and_validate_stock(uow, checkout_data)

            # Lưu dữ liệu Hóa đơn
            invoice_id = self._save_invoice_data(uow, checkout_data)

            # Trừ kho và ghi nhận lịch sử biến động
            self._process_inventory_deduction(uow, product_deduction_map, invoice_id)

            # Ghi log thao tác
            uow.sale_repo.add_invoice_log(invoice_id, 'CREATE', 'Tạo mới hóa đơn bán hàng tại POS')

            # Hoàn tất Transaction
            return checkout_data.code

    # ==========================================
    # CÁC HÀM PRIVATE HỖ TRỢ XỬ LÝ NGHIỆP VỤ
    # ==========================================

    def _prepare_and_validate_stock(self, uow, checkout_data: CheckoutDTO) -> dict:
        """Gộp số lượng theo đơn vị cơ bản và kiểm tra xem kho có đủ hàng không."""
        product_deduction_map = {}
        for item in checkout_data.items:
            base_qty = self._calculate_base_quantity(uow, item.product_id, item.unit_id, item.quantity)
            product_deduction_map[item.product_id] = product_deduction_map.get(item.product_id, 0) + base_qty

        for p_id, required_qty in product_deduction_map.items():
            stock_result = uow.inventory_repo.get_inventory_status(p_id)

            # Xử lý an toàn: Bóc tách số lượng tồn kho bất kể kết quả là dict hay int
            current_stock = 0
            if isinstance(stock_result, dict):
                # Lấy giá trị từ key 'quantity'
                current_stock = stock_result.get('quantity', 0)
            elif isinstance(stock_result, (int, float)):
                current_stock = int(stock_result)

            if current_stock < required_qty:
                product = uow.product_repo.get_product_by_id(p_id)
                raise ValidationException(
                    f"Sản phẩm '{product.name}' không đủ tồn kho! "
                    f"(Còn: {current_stock}, Cần: {required_qty})"
                )
        return product_deduction_map

    def _save_invoice_data(self, uow: UnitOfWork, checkout_data: CheckoutDTO) -> int:
        """Xử lý việc sinh mã và lưu thông tin Hóa đơn (Header + Details)."""
        checkout_data.code = InvoiceCodeGenerator.generate()
        invoice_id = uow.sale_repo.create_invoice(checkout_data)
        uow.sale_repo.create_invoice_items(invoice_id, checkout_data.items)
        return invoice_id

    def _process_inventory_deduction(self, uow, product_deduction_map: dict, invoice_id: int):
        """Xử lý trừ số lượng kho và ghi nhận vào bảng stock_transactions."""
        for p_id, deducted_qty in product_deduction_map.items():
            # Lấy số lượng và tính lại giá trị tồn kho (MAC)
            cursor = uow.connection.cursor(dictionary=True)
            cursor.execute("SELECT quantity, total_value FROM inventory WHERE product_id = %s", (p_id,))
            inv_data = cursor.fetchone()

            old_qty = inv_data['quantity'] if inv_data else 0
            old_total_value = Decimal(str(inv_data['total_value'])) if inv_data and inv_data['total_value'] else 0.0

            new_qty = old_qty - deducted_qty
            unit_cost = (old_total_value / old_qty) if old_qty > 0 else 0
            new_total_value = new_qty * unit_cost

            uow.inventory_repo.update_inventory_status(p_id, new_qty, new_total_value)

            trans_data = {
                'product_id': p_id,
                'qty': -deducted_qty,
                'type': 'SALE',
                'ref_id': invoice_id
            }
            uow.inventory_repo.add_stock_transaction(trans_data)

    def _calculate_base_quantity(self, uow: UnitOfWork, product_id: int, unit_id: int, quantity: int) -> int:
        """Lấy tỷ lệ quy đổi để tính ra số lượng đơn vị cơ bản cần trừ."""
        product = uow.product_repo.get_product_by_id(product_id)

        if product and product.base_unit_id == unit_id:
            return quantity

        cursor = uow.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT ratio FROM unit_conversions WHERE product_id = %s AND to_unit_id = %s",
            (product_id, unit_id)
        )
        conversion = cursor.fetchone()

        if not conversion:
            raise ValidationException(f"Đơn vị tính không hợp lệ hoặc chưa được thiết lập quy đổi cho sản phẩm này!")

        ratio = int(conversion['ratio'])
        return quantity * ratio
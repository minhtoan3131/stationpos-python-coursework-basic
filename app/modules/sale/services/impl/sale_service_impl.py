from decimal import Decimal, ROUND_HALF_UP

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
        Luồng nghiệp vụ xử lý thanh toán và khấu trừ kho tự sửa lỗi chuẩn Enterprise.
        """
        SaleValidator.validate_checkout_data(checkout_data)

        with self.uow_factory() as uow:
            # 1. Gom nhóm số lượng và quy đổi về Đơn vị cơ bản
            product_deduction_map = {}
            for item in checkout_data.items:
                base_qty = self._calculate_base_quantity(uow, item.product_id, item.unit_id, item.quantity)
                product_deduction_map[item.product_id] = product_deduction_map.get(item.product_id, 0) + base_qty

            cogs_allocation_map = {}

            # Khởi tạo danh sách chứa các ID giao dịch kho vừa sinh ra để chờ liên kết hóa đơn
            created_transaction_ids = []

            # 2. Khóa dòng (FOR UPDATE) và thực hiện tính toán tài chính nghịch đảo
            for p_id, sold_qty in product_deduction_map.items():

                # Gọi Repo có chứa khóa dòng FOR UPDATE để cô lập dữ liệu
                inv_data = uow.inventory_repo.get_inventory_status(p_id)
                old_qty = inv_data['quantity']
                old_total_value = Decimal(str(inv_data['total_value']))

                if old_qty < sold_qty:
                    product = uow.product_repo.get_product_by_id(p_id)
                    raise ValidationException(
                        f"Sản phẩm '{product.name}' không đủ tồn kho để thực hiện giao dịch! "
                        f"(Tồn kho thực tế: {old_qty}, Số lượng yêu cầu: {sold_qty})"
                    )

                # Toán học ép giá trị kho lùi (Triệt tiêu rác)
                unit_cost = old_total_value / Decimal(str(old_qty)) if old_qty > 0 else Decimal('0')
                new_qty = old_qty - sold_qty

                if new_qty == 0:
                    new_total_value = Decimal('0.0000')
                else:
                    new_total_value = (new_qty * unit_cost).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

                # Tính nghịch đảo ra COGS thực tế
                total_cogs_for_product = old_total_value - new_total_value
                cogs_allocation_map[p_id] = total_cogs_for_product

                # Thực thi ghi nhận số dư kho mới xuống DB
                uow.inventory_repo.update_inventory_status(p_id, new_qty, new_total_value)

                # GHI LOG VÀ HỨNG LẤY ID TƯỜNG MINH TỪ REPO TRẢ VỀ
                tx_id = uow.inventory_repo.add_stock_transaction({
                    'product_id': p_id,
                    'qty': -sold_qty,
                    'type': 'SALE',
                    'ref_id': None  # Tạm thời để trống
                })
                created_transaction_ids.append(tx_id)  # Lưu vết lại ID

            # 3. Phân bổ chi phí COGS ngược lại cho từng dòng mặt hàng hóa đơn
            for item in checkout_data.items:
                line_base_qty = self._calculate_base_quantity(uow, item.product_id, item.unit_id, item.quantity)
                total_product_sold = product_deduction_map[item.product_id]
                total_product_cogs = cogs_allocation_map[item.product_id]

                if total_product_sold > 0:
                    item.total_cogs_amount = (Decimal(str(line_base_qty)) / Decimal(
                        str(total_product_sold)) * total_product_cogs).quantize(Decimal('0.0001'),
                                                                                rounding=ROUND_HALF_UP)
                else:
                    item.total_cogs_amount = Decimal('0.0000')

            # 4. Ghi nhận Header và chi tiết hóa đơn
            if not checkout_data.code:
                checkout_data.code = InvoiceCodeGenerator.generate()

            invoice_id = uow.sale_repo.create_invoice(checkout_data)
            uow.sale_repo.create_invoice_items(invoice_id, checkout_data.items)

            # ---  GỌI HÀM REPO ĐỂ LIÊN KẾT THEO ID CHÍNH XÁC ---
            uow.inventory_repo.link_stock_transactions_to_invoice(created_transaction_ids, invoice_id)

            # Ghi log thao tác hệ thống
            uow.sale_repo.add_invoice_log(invoice_id, 'CREATE',
                                          'Tạo mới hóa đơn bán hàng tại POS - Đã chốt COGS an toàn bằng danh sách ID.')

            total_qty = sum(item.quantity for item in checkout_data.items)
            final_amount = float(checkout_data.final_amount) if checkout_data.final_amount else 0.0
            log_description = f"SL: {total_qty:,} | Tổng: {final_amount:,.0f} VND"

            uow.activity_log_repo.add_log(
                action_type='SALE',
                reference_code=checkout_data.code,
                description=log_description
            )

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

    def _calculate_base_quantity(self, uow, product_id: int, unit_id: int, quantity: int) -> int:
        product = uow.product_repo.get_product_by_id(product_id)
        if product and product.base_unit_id == unit_id:
            return quantity

        conversion = uow.inventory_repo.get_conversion_info(product_id, unit_id)
        if not conversion:
            raise ValidationException(f"Đơn vị tính không hợp lệ cho sản phẩm ID {product_id}!")

        ratio = int(float(conversion['ratio']))
        return quantity * ratio
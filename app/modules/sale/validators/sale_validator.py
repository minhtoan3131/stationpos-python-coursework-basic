from app.core.exceptions.validation_exception import ValidationException
from app.modules.sale.dtos.sale_dto import CheckoutDTO


class SaleValidator:
    @staticmethod
    def validate_checkout_data(checkout_data: CheckoutDTO) -> None:
        """Kiểm tra các logic kinh doanh cơ bản trước khi thanh toán"""

        # Giỏ hàng trống
        if not checkout_data.items or len(checkout_data.items) == 0:
            raise ValidationException("Giỏ hàng đang trống, không thể thanh toán!")

        # Tiền khách đưa chưa đủ (Chỉ kiểm tra nếu phương thức là tiền mặt)
        if checkout_data.payment_method == 'CASH':
            if checkout_data.cash_received < checkout_data.final_amount:
                raise ValidationException(
                    f"Số tiền khách đưa ({checkout_data.cash_received:,.0f} VND) "
                    f"không đủ để thanh toán hóa đơn ({checkout_data.final_amount:,.0f} VND)."
                )
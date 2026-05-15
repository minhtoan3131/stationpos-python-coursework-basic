class UnitConverter:
    """
    Tiện ích xử lý logic quy đổi số lượng (Từ đơn vị cơ bản sang Sỉ + Lẻ).
    """

    @staticmethod
    def format_conversion_string(total_qty: int, ratio, conv_name: str, base_name: str) -> str:
        # Nếu không có thông tin quy đổi hoặc tỷ lệ không hợp lệ
        if not ratio or not conv_name or float(ratio) <= 0:
            return "---"

        ratio_int = int(float(ratio))
        si_qty = total_qty // ratio_int
        le_qty = total_qty % ratio_int

        if si_qty > 0 and le_qty > 0:
            return f"{si_qty} {conv_name} + {le_qty} {base_name}"
        elif si_qty > 0 and le_qty == 0:
            return f"{si_qty} {conv_name}"
        else:
            return f"{le_qty} {base_name}"
# File: app/modules/product/utils/product_margin_calculator.py

class ProductMarginCalculator:
    @staticmethod
    def calculate_margin_and_status(retail_price: float, cost_price: float) -> tuple[float, str, str]:
        """
        Tính toán biên lợi nhuận lẻ (%) và quyết định trạng thái thị giác (Mã màu Hex).
        Trả về bộ 3 giá trị: (margin_percent, text_hiển_thị, mã_màu_hex)
        """
        retail_val = float(retail_price) if retail_price else 0.0
        cost_val = float(cost_price) if cost_price else 0.0

        # Chốt chặn phòng vệ lỗi chia cho số 0 (ZeroDivisionError)
        if retail_val > 0:
            margin_percent = ((retail_val - cost_val) / retail_val) * 100
        else:
            margin_percent = 0.0

        margin_text = f"{margin_percent:.1f}%"

        # Phân lớp trạng thái tài chính để định hướng thị giác
        if cost_val > retail_val:
            # TRƯỜNG HỢP 1: LỖ VỐN NGUY HIỂM
            return margin_percent, f"{margin_text}", "#ef4444"
        elif cost_val == retail_val and cost_val > 0:
            # TRƯỜNG HỢP 2: HÒA VỐN RỦI RO
            return margin_percent, f"{margin_text}", "#d97706"
        else:
            # TRƯỜNG HỢP 3: BIÊN AN TOÀN
            return margin_percent, margin_text, "#10b981"
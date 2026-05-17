from decimal import Decimal
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


class TaxUIHelper:

    @staticmethod
    def create_numeric_item(value: Decimal) -> QTableWidgetItem:
        """Tạo QTableWidgetItem định dạng tiền tệ và canh lề phải"""
        item = QTableWidgetItem(f"{value:,.0f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    @staticmethod
    def generate_progress_bar_css(total: Decimal, threshold: Decimal) -> str:
        """Sinh mã CSS cho thanh Progress Bar dựa trên tỷ lệ doanh thu / ngưỡng"""
        # Nếu ngưỡng <= 0 (bất thường), mặc định hiển thị đỏ
        if threshold <= Decimal('0'):
            return "QProgressBar::chunk { background-color: #ef4444; border-radius: 9px; }"

        if total <= threshold:
            # Dưới ngưỡng: Xanh hoàn toàn
            return "QProgressBar::chunk { background-color: #10b981; border-radius: 9px; }"
        else:
            # Vượt ngưỡng: Tính toán tỷ lệ để vẽ Gradient xanh -> đỏ
            safe_ratio = float(threshold / total)

            # Xử lý tránh lỗi CSS điểm stop bị âm
            stop_point = max(0.0, safe_ratio - 0.005)

            css = f"""
                QProgressBar::chunk {{
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #4185fa, stop:{stop_point} #4185fa, 
                        stop:{safe_ratio} #ef4444, stop:1 #ef4444
                    );
                    border-radius: 9px;
                }}
            """
            return css
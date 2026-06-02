import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from typing import List
from app.modules.report.dtos.report_dto import RevenueTrendItemDTO, TopProductDTO


class ChartBuilder:
    """Factory Class chịu trách nhiệm khởi tạo và vẽ đồ thị chuyên biệt."""

    @staticmethod
    def build_revenue_trend_chart(revenue_trend: List[RevenueTrendItemDTO]) -> FigureCanvas:
        # Sử dụng subplots rõ ràng thay vì plt.plot dùng chung state toàn cục
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        fig.tight_layout()

        if revenue_trend:
            days = [item.date for item in revenue_trend]
            revs = [float(item.revenue) for item in revenue_trend]
            ax.plot(days, revs, marker='o', color='#3b82f6', linewidth=2)
        else:
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center', color='gray')

        ax.set_title("Xu hướng doanh thu", fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.5)

        return FigureCanvas(fig)

    @staticmethod
    def build_top_products_chart(top_products: List[TopProductDTO]) -> FigureCanvas:
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)

        if top_products:
            # Dùng SKU làm nhãn trục X
            x_labels = [p.sku for p in top_products]
            # Tên đầy đủ dùng cho tooltip
            full_names = [p.product_name for p in top_products]
            sales = [p.quantity for p in top_products]

            bars = ax.bar(x_labels, sales, color='#10b981')

            # Xoay nhãn 45 độ để không bị đè
            plt.xticks(rotation=45, ha='right', fontsize=9)

            # Tích hợp Tooltip: SỬA LỖI bằng cách dùng sel.index
            cursor = mplcursors.cursor(bars, hover=True)
            cursor.connect("add", lambda sel: sel.annotation.set_text(full_names[sel.index]))

        else:
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center', color='gray')

        ax.set_title("Top 5 sản phẩm bán chạy", fontsize=10)
        plt.tight_layout()
        return FigureCanvas(fig)
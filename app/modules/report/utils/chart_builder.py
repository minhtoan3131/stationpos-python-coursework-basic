import matplotlib.pyplot as plt
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
        fig.tight_layout()

        if top_products:
            products = [item.product_name for item in top_products]
            sales = [item.quantity for item in top_products]
            ax.bar(products, sales, color='#10b981')
        else:
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center', color='gray')

        ax.set_title("Top 5 sản phẩm bán chạy", fontsize=10)

        return FigureCanvas(fig)
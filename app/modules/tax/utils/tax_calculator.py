from decimal import Decimal
from typing import List, Tuple


class TaxCalculator:
    """
    Bộ lõi tính toán Thuế suất Hộ Kinh Doanh 2026.
    """

    @staticmethod
    def calculate_total_revenue(monthly_revenues: List[Decimal]) -> Decimal:
        """Tính tổng doanh thu năm từ mảng phân bổ tháng."""
        return sum(monthly_revenues)

    @staticmethod
    def is_over_threshold(total_revenue: Decimal, threshold: Decimal) -> bool:
        """Kiểm tra doanh thu năm có vượt ngưỡng chịu thuế hay không."""
        return total_revenue > threshold

    @staticmethod
    def calculate_monthly_tax_distribution(
            monthly_revenues: List[Decimal],
            monthly_costs: List[Decimal],
            total_revenue: Decimal,
            threshold: Decimal,
            vat_rate_percent: Decimal,
            pit_rate_percent: Decimal,
            pit_method: str = 'FLAT_RATE'
    ) -> List[Tuple[Decimal, Decimal, Decimal]]:
        """
        Phân bổ nghĩa vụ thuế cho từng tháng dựa trên tỷ trọng doanh thu phát sinh thực tế.
        Thực thi thuật toán dựa TRỰC TIẾP và KHÔNG CAN THIỆP vào bộ tham số định biên truyền vào.

        Trả về List các dòng Tuple: (VAT_Tháng, PIT_Tháng, Tổng_Thuế_Tháng)
        """
        # CHỐT CHUẨN PHÁP LÝ: Nếu tổng doanh thu năm nằm trong vùng an toàn (dưới ngưỡng), miễn thuế hoàn toàn
        if total_revenue <= threshold or total_revenue == Decimal('0'):
            return [(Decimal('0'), Decimal('0'), Decimal('0')) for _ in monthly_revenues]

        # -----------------------------------------------------------------
        # 1. TÍNH THUẾ GTGT: Áp dụng trực tiếp tỷ lệ định biên thu từ đồng đầu tiên
        # -----------------------------------------------------------------
        vat_rate = vat_rate_percent / Decimal('100')
        total_vat = total_revenue * vat_rate

        # -----------------------------------------------------------------
        # 2. TÍNH THUẾ TNCN: Rẽ nhánh xử lý theo Phương pháp người dùng chọn
        # -----------------------------------------------------------------
        total_pit = Decimal('0')
        pit_rate = pit_rate_percent / Decimal('100')

        if pit_method == 'FLAT_RATE':
            # Phương pháp Khoán: Chỉ tính thuế trên phần doanh thu chênh lệch vượt ngưỡng cơ sở
            taxable_revenue_pit = total_revenue - threshold
            total_pit = taxable_revenue_pit * pit_rate

        elif pit_method == 'BOOKKEEPING':
            # Phương pháp Sổ sách: Tính theo tỷ lệ trực tiếp trên Lợi nhuận kế toán (Doanh thu - Chi phí)
            total_cost = sum(monthly_costs)
            taxable_profit = total_revenue - total_cost
            # Tiền thuế không được âm nếu cửa hàng kinh doanh thua lỗ ở kỳ quyết toán
            total_pit = max(Decimal('0'), taxable_profit) * pit_rate

        # -----------------------------------------------------------------
        # 3. PHÂN BỔ KẾT QUẢ NGƯỢC LẠI CHO 12 THÁNG (Theo tỷ trọng đóng góp doanh thu)
        # -----------------------------------------------------------------
        results = []
        for rev in monthly_revenues:
            if rev == Decimal('0'):
                results.append((Decimal('0'), Decimal('0'), Decimal('0')))
                continue

            # Tính toán tỷ trọng phân phối dòng tiền của tháng so với tổng thể năm
            ratio = rev / total_revenue
            month_vat = total_vat * ratio
            month_pit = total_pit * ratio
            results.append((month_vat, month_pit, month_vat + month_pit))

        return results
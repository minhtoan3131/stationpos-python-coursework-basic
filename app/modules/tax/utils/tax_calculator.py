from decimal import Decimal
from typing import List, Tuple


class TaxCalculator:

    @staticmethod
    def calculate_total_revenue(monthly_revenues: List[Decimal]) -> Decimal:
        """Tính tổng doanh thu năm."""
        return sum(monthly_revenues)

    @staticmethod
    def is_over_threshold(total_revenue: Decimal, threshold: Decimal) -> bool:
        """Kiểm tra doanh thu có vượt ngưỡng miễn thuế hay không."""
        return total_revenue > threshold

    @staticmethod
    def calculate_taxable_amount(total_revenue: Decimal, threshold: Decimal) -> Decimal:
        """Tính phần doanh thu phải chịu thuế (chỉ tính phần vượt ngưỡng)."""
        return max(Decimal('0'), total_revenue - threshold)

    @staticmethod
    def calculate_monthly_tax_distribution(
            monthly_revenues: List[Decimal],
            total_revenue: Decimal,
            threshold: Decimal,
            vat_rate_percent: Decimal,
            pit_rate_percent: Decimal
    ) -> List[Tuple[Decimal, Decimal, Decimal]]:
        """
        Phân bổ số tiền thuế phải nộp cho từng tháng dựa trên tỷ trọng doanh thu.
        Trả về List các Tuple: (VAT_Tháng, PIT_Tháng, Tổng_Thuế_Tháng)
        """
        if total_revenue <= threshold or total_revenue == Decimal('0'):
            # Dưới ngưỡng thì thuế các tháng bằng 0
            return [(Decimal('0'), Decimal('0'), Decimal('0')) for _ in monthly_revenues]

        # Chuyển đổi % thành số thập phân (VD: 1.0% -> 0.01)
        vat_rate = vat_rate_percent / Decimal('100')
        pit_rate = pit_rate_percent / Decimal('100')

        taxable_amount = total_revenue - threshold
        total_vat = taxable_amount * vat_rate
        total_pit = taxable_amount * pit_rate

        results = []
        for rev in monthly_revenues:
            if rev == Decimal('0'):
                results.append((Decimal('0'), Decimal('0'), Decimal('0')))
                continue

            # Phân bổ thuế dựa trên tỷ trọng doanh thu của tháng đó so với cả năm
            ratio = rev / total_revenue
            month_vat = total_vat * ratio
            month_pit = total_pit * ratio
            results.append((month_vat, month_pit, month_vat + month_pit))

        return results
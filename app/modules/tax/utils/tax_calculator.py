from decimal import Decimal
from typing import List, Tuple


class TaxCalculator:
    # =================================================================
    # CẤU HÌNH BIỂU THUẾ THEO NGHỊ ĐỊNH 68/2026/NĐ-CP
    # =================================================================
    LIMIT_BOOKKEEPING_MANDATORY = Decimal('3000000000')  # Mốc 3 Tỷ bắt buộc sổ sách
    LIMIT_LARGE_SCALE = Decimal('50000000000')  # Mốc 50 Tỷ quy mô lớn

    RATE_PIT_BOOKKEEPING_BASE = Decimal('0.15')  # 15% cho mốc dưới 3 Tỷ
    RATE_PIT_BOOKKEEPING_LARGE = Decimal('0.17')  # 17% cho mốc 3 - 50 Tỷ
    RATE_PIT_BOOKKEEPING_MEGA = Decimal('0.20')  # 20% cho mốc trên 50 Tỷ

    # =================================================================

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
            monthly_costs: List[Decimal],
            total_revenue: Decimal,
            threshold: Decimal,
            vat_rate_percent: Decimal,
            pit_rate_percent: Decimal,
            pit_method: str = 'FLAT_RATE'
    ) -> List[Tuple[Decimal, Decimal, Decimal]]:
        """
        Phân bổ số tiền thuế phải nộp cho từng tháng dựa trên tỷ trọng doanh thu.
        Áp dụng biểu thuế phân khúc theo Luật sửa đổi và Nghị định 68/2026/NĐ-CP.

        Trả về List các Tuple: (VAT_Tháng, PIT_Tháng, Tổng_Thuế_Tháng)
        """
        # CHỐT CHUẨN: Doanh thu từ 1 tỷ trở xuống (<= threshold) được miễn toàn bộ thuế
        if total_revenue <= threshold or total_revenue == Decimal('0'):
            return [(Decimal('0'), Decimal('0'), Decimal('0')) for _ in monthly_revenues]

        # -----------------------------------------------------------------
        # 1. THUẾ GTGT: Tính trực tiếp trên tổng doanh thu từ đồng đầu tiên (Áp dụng cho tất cả các nhóm 2, 3, 4)
        # -----------------------------------------------------------------
        vat_rate = vat_rate_percent / Decimal('100')
        total_vat = total_revenue * vat_rate

        # -----------------------------------------------------------------
        # 2. THUẾ THU NHẬP CÁ NHÂN: Phân cấp theo mốc chặn trên (Sử dụng toán tử <=)
        # -----------------------------------------------------------------
        total_cost = sum(monthly_costs)
        total_pit = Decimal('0')

        if total_revenue <= TaxCalculator.LIMIT_BOOKKEEPING_MANDATORY:
            # PHÂN KHÚC VỪA VÀ NHỎ (Từ trên 1 tỷ đến mốc 3 tỷ): Cho phép tự chọn phương pháp
            if pit_method == 'FLAT_RATE':
                # Cách 1: Khoán % trên doanh thu chênh lệch vượt ngưỡng (Có trừ ngưỡng)
                taxable_revenue_pit = total_revenue - threshold
                total_pit = taxable_revenue_pit * (pit_rate_percent / Decimal('100'))
            elif pit_method == 'BOOKKEEPING':
                # Cách 2: Sổ sách kế toán = 15% trên Lợi nhuận thực tế (KHÔNG TRỪ NGƯỠNG)
                taxable_profit = total_revenue - total_cost
                total_pit = max(Decimal('0'), taxable_profit) * TaxCalculator.RATE_PIT_BOOKKEEPING_BASE

        elif total_revenue <= TaxCalculator.LIMIT_LARGE_SCALE:
            # PHÂN KHÚC QUY MÔ LỚN (Từ trên 3 tỷ đến mốc 50 tỷ): Bắt buộc Sổ sách 17% (KHÔNG TRỪ NGƯỠNG)
            taxable_profit = total_revenue - total_cost
            total_pit = max(Decimal('0'), taxable_profit) * TaxCalculator.RATE_PIT_BOOKKEEPING_LARGE

        else:
            # PHÂN KHÚC ĐẠI QUY MÔ (Từ trên 50 tỷ trở lên): Bắt buộc Sổ sách 20% (KHÔNG TRỪ NGƯỠNG)
            taxable_profit = total_revenue - total_cost
            total_pit = max(Decimal('0'), taxable_profit) * TaxCalculator.RATE_PIT_BOOKKEEPING_MEGA

        # -----------------------------------------------------------------
        # 3. PHÂN BỔ TIỀN THUẾ NGƯỢC LẠI CHO 12 THÁNG (Theo tỷ trọng doanh thu)
        # -----------------------------------------------------------------
        results = []
        for rev in monthly_revenues:
            if rev == Decimal('0'):
                results.append((Decimal('0'), Decimal('0'), Decimal('0')))
                continue

            ratio = rev / total_revenue
            month_vat = total_vat * ratio
            month_pit = total_pit * ratio
            results.append((month_vat, month_pit, month_vat + month_pit))

        return results
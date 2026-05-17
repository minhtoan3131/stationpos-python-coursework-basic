import pytest
from decimal import Decimal
from app.modules.tax.utils.tax_calculator import TaxCalculator


@pytest.mark.parametrize("monthly_revs, total_rev, threshold, vat_rate, pit_rate, expected_month_1_tax", [
    # Kịch bản 1: Dưới ngưỡng -> Thuế bằng 0
    (
            [Decimal('100'), Decimal('200')], Decimal('300'), Decimal('500'),
            Decimal('1.0'), Decimal('0.5'),
            Decimal('0')
    ),
    # Kịch bản 2: Vượt ngưỡng nhưng tháng 1 không bán được gì -> Thuế tháng 1 = 0
    (
            [Decimal('0'), Decimal('2000')], Decimal('2000'), Decimal('1000'),
            Decimal('1.0'), Decimal('0.5'),
            Decimal('0')
    ),
    # Kịch bản 3: Vượt ngưỡng, tính toán số lẻ (Tỷ lệ 1.5% của phần vượt)
    (
            [Decimal('500000'), Decimal('500000')], Decimal('1000000'), Decimal('800000'),
            Decimal('1.0'), Decimal('0.5'),
            Decimal('1500')  # Phần vượt: 200k. Tổng thuế: 3k. Tháng 1 gánh 50% = 1500
    )
])
def test_calculate_monthly_tax_distribution(
        monthly_revs, total_rev, threshold, vat_rate, pit_rate, expected_month_1_tax
):
    # Padding cho đủ 12 tháng
    padded_revs = monthly_revs + [Decimal('0')] * (12 - len(monthly_revs))

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=padded_revs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=vat_rate,
        pit_rate_percent=pit_rate
    )

    # Kết quả trả về là list các tuple: (VAT, PIT, TOTAL_TAX)
    vat_1, pit_1, total_tax_1 = results[0]

    assert total_tax_1 == expected_month_1_tax
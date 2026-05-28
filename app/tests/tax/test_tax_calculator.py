import pytest
from decimal import Decimal
from app.modules.tax.utils.tax_calculator import TaxCalculator


# =================================================================
# 1. KIỂM THỬ CÁC HÀM TIỆN ÍCH CƠ SỞ (BASE UTILITIES)
# =================================================================

def test_calculate_total_revenue_accumulates_correctly():
    """RÀNG BUỘC: Tổng doanh thu năm phải bằng chính xác tổng 12 tháng cộng lại, không lệch 1 đồng."""
    monthly_revs = [Decimal('100000000')] * 12  # 100M mỗi tháng
    total = TaxCalculator.calculate_total_revenue(monthly_revs)
    assert total == Decimal('1200000000')  # 1.2 Tỷ


@pytest.mark.parametrize("total_rev, threshold, expected", [
    (Decimal('999999999'), Decimal('1000000000'), False),  # Dưới ngưỡng 1 đồng
    (Decimal('1000000000'), Decimal('1000000000'), False),  # Bằng đúng ngưỡng miễn thuế
    (Decimal('1000000001'), Decimal('1000000000'), True),  # Vượt ngưỡng 1 đồng
])
def test_is_over_threshold_edge_cases(total_rev, threshold, expected):
    """RÀNG BUỘC NGHIỆP VỤ: Doanh thu phải LỚN HƠN hẳn ngưỡng miễn thuế mới tính là vượt ngưỡng."""
    assert TaxCalculator.is_over_threshold(total_rev, threshold) == expected


# =================================================================
# 2. KIỂM THỬ BIẾN ĐỘNG PHƯƠNG PHÁP KHOÁN (FLAT RATE METHOD)
# =================================================================

def test_flat_rate_under_or_equal_threshold_exempts_all_taxes():
    """
    NGHIỆP VỤ HỘP ĐEN: Nếu tổng doanh thu năm <= ngưỡng miễn thuế,
    thì nghĩa vụ thuế (cả VAT và PIT) của TẤT CẢ các tháng phải bằng 0.
    """
    monthly_revs = [Decimal('100000000')] * 10 + [Decimal('0'), Decimal('0')]  # 1 Tỷ
    monthly_costs = [Decimal('50000000')] * 12  # Chi phí (Không ảnh hưởng đến thuế khoán)
    total_rev = Decimal('1000000000')
    threshold = Decimal('1000000000')

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=Decimal('1.0'),
        pit_rate_percent=Decimal('0.5'),
        pit_method='FLAT_RATE'
    )

    for vat, pit, total in results:
        assert vat == Decimal('0')
        assert pit == Decimal('0')
        assert total == Decimal('0')


def test_flat_rate_over_threshold_calculates_correctly():
    """
    NGHIỆP VỤ KHOÁN TỰ DO:
    - Thuế GTGT (VAT): Tính trên TỔNG doanh thu từ đồng đầu tiên (Total * Rate).
    - Thuế TNCN (PIT): Chỉ tính trên PHẦN VƯỢT NGƯỠNG ((Total - Threshold) * Rate).
    - Phân bổ: Canh lề hiển thị 12 tháng theo tỷ trọng dòng tiền đóng góp thực tế.
    """
    monthly_revs = [Decimal('200000000')] * 10 + [Decimal('0'), Decimal('0')]  # Tổng 2 Tỷ
    monthly_costs = [Decimal('0')] * 12
    total_rev = Decimal('2000000000')
    threshold = Decimal('1000000000')  # Ngưỡng 1 Tỷ

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=Decimal('1.0'),  # 1% VAT
        pit_rate_percent=Decimal('0.5'),  # 0.5% PIT
        pit_method='FLAT_RATE'
    )

    # Kỳ vọng: Tổng VAT = 20M, Tổng PIT = (2 Tỷ - 1 Tỷ) * 0.5% = 5M.
    # 10 tháng có doanh thu chia đều gánh vác: VAT = 2M, PIT = 500k, Tổng = 2.5M
    total_calculated_vat = Decimal('0')
    total_calculated_pit = Decimal('0')

    for idx, (vat, pit, total) in enumerate(results):
        if idx < 10:
            assert vat == Decimal('2000000')
            assert pit == Decimal('500000')
            assert total == Decimal('2500000')
        else:
            assert vat == Decimal('0')
            assert pit == Decimal('0')
            assert total == Decimal('0')

        total_calculated_vat += vat
        total_calculated_pit += pit

    assert total_calculated_vat == Decimal('20000000')
    assert total_calculated_pit == Decimal('5000000')


# =================================================================
# 3. KIỂM THỬ BIẾN ĐỘNG PHƯƠNG PHÁP SỔ SÁCH (BOOKKEEPING METHOD)
# =================================================================

def test_bookkeeping_positive_profit_calculates_correctly():
    """
    NGHIỆP VỤ SỔ SÁCH KHI KINH DOANH CÓ LÃI:
    - Thuế GTGT (VAT): Tính trên TỔNG doanh thu từ đồng đầu tiên (Total * Rate).
    - Thuế TNCN (PIT): Tính trực tiếp trên LỢI NHUẬN (Doanh thu - Chi phí) * Rate, KHÔNG TRỪ NGƯỠNG CƠ SỞ.
    """
    monthly_revs = [Decimal('100000000')] * 12  # Tổng doanh thu: 1.2 Tỷ
    monthly_costs = [Decimal('50000000')] * 12  # Tổng chi phí: 600 Triệu
    total_rev = Decimal('1200000000')
    threshold = Decimal('1000000000')

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=Decimal('1.0'),
        pit_rate_percent=Decimal('15.0'),  # Tùy chỉnh tự do 15% trên UI
        pit_method='BOOKKEEPING'
    )

    # Lợi nhuận = 600M -> PIT năm = 600M * 15% = 90M. VAT năm = 1.2 Tỷ * 1% = 12M
    # Phân bổ đều 12 tháng: VAT = 1M, PIT = 7.5M, Tổng = 8.5M
    sum_vat = sum(r[0] for r in results)
    sum_pit = sum(r[1] for r in results)

    for vat, pit, total in results:
        assert vat == Decimal('1000000')
        assert pit == Decimal('7500000')
        assert total == Decimal('8500000')

    assert sum_vat == Decimal('12000000')
    assert sum_pit == Decimal('90000000')


def test_bookkeeping_negative_profit_zeroes_pit_but_keeps_vat():
    """
    SĂN LỖI BIÊN NGHIỆM VỤ (KINH DOANH THUA LỖ):
    - Hộ kinh doanh phát sinh doanh thu vượt ngưỡng nhưng chi phí mặt bằng quá cao dẫn đến thua lỗ (Lợi nhuận âm).
    - Kỳ vọng: Thuế GTGT vẫn tính bình thường, nhưng Thuế TNCN bắt buộc phải bằng 0, TUYỆT ĐỐI KHÔNG SINH THUẾ ÂM.
    """
    monthly_revs = [Decimal('200000000')] * 10 + [Decimal('0'), Decimal('0')]  # Doanh thu: 2 Tỷ
    monthly_costs = [Decimal('250000000')] * 10 + [Decimal('0'), Decimal('0')]  # Chi phí: 2.5 Tỷ (Lỗ 500M)
    total_rev = Decimal('2000000000')
    threshold = Decimal('1000000000')

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=Decimal('1.0'),
        pit_rate_percent=Decimal('15.0'),
        pit_method='BOOKKEEPING'
    )

    for idx, (vat, pit, total) in enumerate(results):
        if idx < 10:
            assert vat == Decimal('2000000')
            assert pit == Decimal('0')  # Kinh doanh lỗ -> PIT đứng im bằng 0
            assert total == Decimal('2000000')
        else:
            assert vat == Decimal('0')
            assert pit == Decimal('0')
            assert total == Decimal('0')


# =================================================================
# 4. KIỂM THỬ AN TOÀN TOÀN VẸN HIỂN THỊ (EDGE CASES DISPLAY)
# =================================================================

def test_zero_revenue_across_all_months_returns_zero_taxes():
    """KỊCH BẢN BIÊN: Hộ kinh doanh đóng cửa hoặc không phát sinh bất kỳ dòng tiền nào cả năm."""
    monthly_revs = [Decimal('0')] * 12
    monthly_costs = [Decimal('0')] * 12

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=Decimal('0'),
        threshold=Decimal('1000000000'),
        vat_rate_percent=Decimal('1.0'),
        pit_rate_percent=Decimal('0.5'),
        pit_method='FLAT_RATE'
    )

    for vat, pit, total in results:
        assert vat == Decimal('0')
        assert pit == Decimal('0')
        assert total == Decimal('0')


def test_month_with_exactly_zero_revenue_has_zero_tax_allocation():
    """
    RÀNG BUỘC HIỂN THỊ NGƯỜI DÙNG:
    Nếu trong năm có tháng hộ kinh doanh nghỉ dưỡng bệnh (Doanh thu tháng = 0),
    thì dù tổng năm có vượt ngưỡng bao nhiêu, tiền thuế hiển thị của tháng đó bắt buộc phải bằng 0.
    """
    monthly_revs = [Decimal('100000000')] * 11 + [Decimal('0')]  # Tháng 12 đóng cửa nghỉ Tết
    monthly_costs = [Decimal('0')] * 12
    total_rev = Decimal('1100000000')
    threshold = Decimal('1000000000')

    results = TaxCalculator.calculate_monthly_tax_distribution(
        monthly_revenues=monthly_revs,
        monthly_costs=monthly_costs,
        total_revenue=total_rev,
        threshold=threshold,
        vat_rate_percent=Decimal('1.0'),
        pit_rate_percent=Decimal('0.5'),
        pit_method='FLAT_RATE'
    )

    # Kiểm tra tháng thứ 12 (Index 11) tiền thuế phân bổ bắt buộc phải sạch bóng
    vat_m12, pit_m12, total_m12 = results[11]
    assert vat_m12 == Decimal('0')
    assert pit_m12 == Decimal('0')
    assert total_m12 == Decimal('0')
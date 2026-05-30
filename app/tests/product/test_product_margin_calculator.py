# File: app/tests/product/test_product_margin_calculator.py
import pytest

from app.modules.product.ultils.product_margin_calculator import ProductMarginCalculator


def test_should_calculate_correct_margin_and_return_green_when_profitable():
    """
    KIỂM THỬ: LÃI (BIÊN AN TOÀN KHỎE MẠNH)
    Điều kiện: Giá bán 5,000 đ, Giá vốn MAC 4,000 đ
    Kỳ vọng: Biên LN = 20.0%, Text = '20.0%', Mã màu lục = '#10b981'
    """
    margin_pct, text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
        retail_price=5000.0,
        cost_price=4000.0
    )

    assert margin_pct == 20.0
    assert text == "20.0%"
    assert hex_color == "#10b981"


def test_should_calculate_negative_margin_and_return_red_with_alert_icon_when_at_loss():
    """
    KIỂM THỬ: LỖ (THỦNG GIÁ VỐN NGUY HIỂM)
    Điều kiện: Giá bán 10,000 đ, Giá vốn MAC 15,000 đ
    Kỳ vọng: Biên LN = -50.0%, Text có đuôi '🚨 LỖ', Mã màu đỏ = '#ef4444'
    """
    margin_pct, text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
        retail_price=10000.0,
        cost_price=15000.0
    )

    assert margin_pct == -50.0
    assert text == "-50.0%"
    assert hex_color == "#ef4444"


def test_should_return_zero_margin_and_orange_with_warning_icon_when_at_break_even():
    """
    KIỂM THỬ: HÒA VỐN
    Điều kiện: Giá bán 5,000 đ, Giá vốn MAC 5,000 đ
    Kịch bản: Giá bán bằng khít giá vốn
    Kỳ vọng: Biên LN = 0.0%, Text có đuôi '⚠️ HÒA', Mã màu cam = '#d97706'
    """
    margin_pct, text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
        retail_price=5000.0,
        cost_price=5000.0
    )

    assert margin_pct == 0.0
    assert text == "0.0%"
    assert hex_color == "#d97706"


def test_should_handle_edge_case_resiliently_when_retail_price_is_zero():
    """
    KIỂM THỬ: CHỐT CHẶN BIÊN GIỚI HẠN (Giá bán lẻ bằng 0)
    Kịch bản: Sản phẩm là quà tặng kèm hoặc chưa kịp định giá bán lẻ
    Kỳ vọng: Không crash lỗi ZeroDivisionError, biên LN rơi về 0.0%, màu đỏ khi đã có giá nhập, màu lục khi chưa có giá nhập
    """
    try:
        margin_pct, text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
            retail_price=0.0,
            cost_price=2000.0
        )
    except ZeroDivisionError:
        pytest.fail("Hệ thống sập! Vi phạm chốt chặn an toàn toán học khi chia cho số 0.")

    assert margin_pct == 0.0
    assert text == "0.0%"
    assert hex_color == "#ef4444"

    try:
        margin_pct, text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
            retail_price=0.0,
            cost_price=0.0
        )
    except ZeroDivisionError:
        pytest.fail("Hệ thống sập! Vi phạm chốt chặn an toàn toán học khi chia cho số 0.")

    assert margin_pct == 0.0
    assert text == "0.0%"
    assert hex_color == "#10b981"
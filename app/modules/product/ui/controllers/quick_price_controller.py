from PyQt6.QtWidgets import QDialog, QMessageBox
from app.modules.product.services.product_service import ProductService
from app.modules.product.ui.generated.ui_quick_price_dialog import Ui_QuickPriceDialog


class QuickPriceDialogController(QDialog):
    def __init__(self, product_id: int, sku: str, name: str, base_unit: str, conv_display: str, ratio: float,
                 mac_price: float, retail_price: float, wholesale_price: float, product_service: ProductService):
        super().__init__()
        self.ui = Ui_QuickPriceDialog()
        self.ui.setupUi(self)

        self.product_id = product_id
        self.product_service = product_service
        self.ratio = ratio if (ratio and ratio > 0) else 1.0  # Lưu tỷ lệ quy đổi để tính toán

        # 1. Đổ dữ liệu định danh Master
        self.ui.lbl_product_info.setText(f"📦 {sku} | {name}")

        # 2. Đổ dữ liệu vào Khung tham chiếu thông minh (Tự quy đổi nhân hệ số hộp)
        self.ui.lbl_base_unit_val.setText(base_unit)
        self.ui.lbl_conv_val.setText(f"{conv_display}")

        # Tính toán giá vốn tổng của cả hộp để người dùng dễ nhìn đối chiếu
        mac_box = mac_price * self.ratio
        self.ui.lbl_mac_val.setText(f"{mac_price:,.0f}đ / {base_unit}  ➔  (Vốn cả hộp: {mac_box:,.0f} VND)")

        # 3. Đổ dữ liệu mặc định vào các ô nhập giá
        self.ui.spn_retail_price.setValue(int(retail_price))
        self.ui.spn_wholesale_price.setValue(int(wholesale_price))

        # Khống chế định dạng tiền tệ và UX chống cuộn chuột
        self.ui.spn_retail_price.setGroupSeparatorShown(True)
        self.ui.spn_wholesale_price.setGroupSeparatorShown(True)
        self.ui.spn_retail_price.setDecimals(0)
        self.ui.spn_wholesale_price.setDecimals(0)
        self.ui.spn_retail_price.wheelEvent = lambda e: e.ignore()
        self.ui.spn_wholesale_price.wheelEvent = lambda e: e.ignore()

        # 🔔 ĐÃ THÊM: Kết nối sự kiện gõ chữ thay đổi số để tự động chia lẻ tiền thời gian thực
        self.ui.spn_wholesale_price.valueChanged.connect(self.calculate_single_wholesale_price)
        # Chạy kiểm tra kích hoạt nhãn hiển thị ngay lần đầu mở form
        self.calculate_single_wholesale_price(self.ui.spn_wholesale_price.value())

        # Đấu nối sự kiện click nút
        self.ui.btn_save.clicked.connect(self.save_prices)
        self.ui.btn_cancel.clicked.connect(self.reject)

    def calculate_single_wholesale_price(self, current_box_price):
        """Hàm tự động tính nhẩm: Lấy giá cả hộp chia cho tỷ lệ để hiển thị giá lẻ tương đương."""
        single_equiv = current_box_price / self.ratio
        # Mượn tạm tooltip hoặc gán trực tiếp chữ gợi ý động vào phần nhãn để người dùng quan sát trực quan
        if self.ratio > 1:
            self.ui.lbl_wholesale.setText(
                f"Giá bán sỉ mới (Cả hộp)  ➔  [ Tương đương: {single_equiv:,.0f} VND / ĐVT lẻ ]")
        else:
            self.ui.lbl_wholesale.setText("Giá bán sỉ mới (VND):")

    def save_prices(self):
        try:
            retail = float(self.ui.spn_retail_price.value())
            wholesale = float(self.ui.spn_wholesale_price.value())

            self.product_service.update_product_prices(self.product_id, retail, wholesale)
            QMessageBox.information(self, "Thành công", "Cập nhật giá bán mới thành công!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi hệ thống", f"Không thể lưu giá bán:\n{str(e)}")
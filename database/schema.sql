DROP DATABASE IF EXISTS pos_vpp;
CREATE DATABASE pos_vpp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pos_vpp;

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    phone VARCHAR(20),
    address TEXT
);

CREATE TABLE units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);


CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    barcode VARCHAR(50),
    category_id INT,
    supplier_id INT, -- Nhà cung cấp mặc định, chứ không phải là thực tế
    base_unit_id INT,
    cost_price DECIMAL(15,4), -- mac hiện tại của sản phẩm
    retail_price DECIMAL(15,4),
    wholesale_price DECIMAL(15,4),
    min_stock INT DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (base_unit_id) REFERENCES units(id)
);

CREATE TABLE unit_conversions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    from_unit_id INT,
    to_unit_id INT,
    ratio DECIMAL(10,2),

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (from_unit_id) REFERENCES units(id),
    FOREIGN KEY (to_unit_id) REFERENCES units(id),
    UNIQUE(product_id, from_unit_id, to_unit_id)
);

CREATE TABLE inventory (
    product_id INT PRIMARY KEY,
    quantity INT DEFAULT 0,
    updated_at DATETIME,
    total_value DECIMAL(15,4) DEFAULT 0, -- Tổng giá trị tồn kho của sản phầm này hiện tại

    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Bảng lưu thông tin chung của Phiếu nhập (Header)
CREATE TABLE purchase_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,       -- Mã phiếu nhập (VD: PN-20231027-001)
    supplier_id INT,                        
    total_amount DECIMAL(15,4),             -- Tổng giá trị phiếu nhập
    note TEXT,                              -- Ghi chú (Lý do, số hóa đơn gốc...)
    status ENUM('COMPLETED','CANCELLED') DEFAULT 'COMPLETED',
    cancel_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

-- Bảng lưu chi tiết từng món hàng trong Phiếu nhập (Lines/Details)
CREATE TABLE purchase_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT,
    product_id INT,
    unit_id INT,
    quantity INT,
    unit_price DECIMAL(15,4),
    total_price DECIMAL(15,4),
    actual_cost_at_import DECIMAL(15, 4) DEFAULT 0.0000, -- giá vốn gốc tại thời điểm nhập
    
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (unit_id) REFERENCES units(id)
);

CREATE TABLE stock_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    change_quantity INT,
    type ENUM('IMPORT', 
				'SALE', 
				'ADJUST', 
				'CANCEL', 
				'ADJUST_VARIANCE', 
				'DATA_CORRECTION', 
				'ANOMALY_ADJUSTMENT') NOT NULL,
    variance_amount DECIMAL(15, 4) DEFAULT 0.0000, -- Cột này dùng để ghi lại số tiền 'rác' còn sót lại khi ép kho về 0
    note TEXT NULL,
    reference_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id)
);


CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    created_at DATETIME,
    total_amount DECIMAL(15,4),
    discount DECIMAL(15,4) DEFAULT 0,
    final_amount DECIMAL(15,4),
    payment_method ENUM('CASH', 'TRANSFER') DEFAULT 'CASH', 
    cash_received DECIMAL(15,4) DEFAULT 0,
    status ENUM('COMPLETED','CANCELLED') DEFAULT 'COMPLETED',
    cancel_reason TEXT
);


CREATE TABLE invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT,
    product_id INT,
    unit_id INT,
    quantity INT,
    cost_price DECIMAL(15,4),
    unit_price DECIMAL(15,4),
    total_price DECIMAL(15,4),
    total_cogs_amount DECIMAL(15, 4) DEFAULT 0.0000, -- Tổng giá vốn hàng bán tại thời điểm giao dịch (Snapshot)

    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (unit_id) REFERENCES units(id)
);


CREATE TABLE invoice_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT,
    action ENUM('CREATE','UPDATE','CANCEL'),
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_name VARCHAR(255),
    address TEXT,
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value TEXT,
    description VARCHAR(255)
);
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES
('TAX_MID_SCALE_LIMIT', '3000000000', 'Mốc giới hạn doanh thu bắt buộc sổ sách kế toán'),
('TAX_LARGE_SCALE_LIMIT', '50000000000', 'Mốc giới hạn doanh thu lớn nhất'),
('STORE_NAME', 'Văn phòng phẩm', 'Tên cửa hàng hiển thị trên đầu hóa đơn'),
('STORE_PHONE', '0901 234 567', 'Số điện thoại liên hệ của cửa hàng'),
('STORE_ADDRESS', 'Hà Nội', 'Địa chỉ chi tiết của cửa hàng'),
('PRINT_PAPER_SIZE', 'K80', 'Khổ giấy in hóa đơn mặc định (K80 hoặc K58)'),
('RECEIPT_FOOTER', 'Cảm ơn quý khách, hẹn gặp lại!', 'Lời chúc hoặc thông điệp in cuối hóa đơn');



-- 1. Bảng Master: Lưu tổng quan năm quyết toán thuế
CREATE TABLE tax_ledger (
    id INT AUTO_INCREMENT PRIMARY KEY,
    apply_year INT UNIQUE NOT NULL,           -- Năm chốt sổ
    total_revenue DECIMAL(15,2) NOT NULL,     -- Doanh thu tổng cả năm tại thời điểm chốt
    total_cost DECIMAL(15,2) NOT NULL,        -- Chi phí tổng cả năm tại thời điểm chốt
    final_vat_amount DECIMAL(15,2) NOT NULL,     -- Tổng thuế GTGT của cả năm
    final_pit_amount DECIMAL(15,2) NOT NULL,     -- Tổng thuế TNCN của cả năm
    pit_method ENUM('FLAT_RATE', 'BOOKKEEPING') NOT NULL, -- Phương pháp áp dụng cho năm đó
    threshold_amount DECIMAL(15,2) NOT NULL DEFAULT 1000000000.00,
    vat_percent DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    pit_percent DECIMAL(5,2) NOT NULL DEFAULT 0.50,
    status ENUM('DRAFT', 'CLOSED') DEFAULT 'DRAFT', -- DRAFT: Kết xuất tạm; CLOSED: Khóa sổ vĩnh viễn bằng PIN
    finalized_at DATETIME DEFAULT NULL,       -- Thời điểm nhập mã PIN khóa sổ thành công
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Bảng Detail: Lưu vết đóng băng chi tiết 12 tháng của năm đó
CREATE TABLE tax_ledger_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tax_ledger_id INT NOT NULL,               -- Foreign Key nối với bảng Master ở trên
    month INT NOT NULL,                       -- Từ tháng 1 đến tháng 12
    revenue DECIMAL(15,2) NOT NULL,           -- Doanh thu thực tế đóng băng của tháng đó
    cost DECIMAL(15,2) NOT NULL,              -- Chi phí thực tế đóng băng của tháng đó
    vat_amount DECIMAL(15,2) NOT NULL,        -- Thuế GTGT phân bổ của tháng đó
    pit_amount DECIMAL(15,2) NOT NULL,        -- Thuế TNCN phân bổ của tháng đó
    
    FOREIGN KEY (tax_ledger_id) REFERENCES tax_ledger(id) ON DELETE CASCADE,
    UNIQUE KEY ukey_ledger_month (tax_ledger_id, month)
);




-- View Tổng hợp Hóa đơn và Lợi nhuận
-- Mục đích: Tính toán chính xác doanh thu (lúc này là total_amount), tổng giá vốn (COGS), và lợi nhuận gộp của từng hóa đơn.
-- Ứng dụng UI: Phục vụ trực tiếp cho 3 thẻ KPI (Doanh thu, Lợi nhuận gộp, Số hóa đơn) và biểu đồ Xu hướng doanh thu.
CREATE OR REPLACE VIEW vw_report_invoice_summary AS
SELECT
    i.id AS invoice_id,
    i.code AS invoice_code,
    i.created_at,
    DATE(i.created_at) AS sale_date,
    i.payment_method,
    i.total_amount AS revenue, -- total_amount vì doanh thu giờ là tổng tiền thực thu
    IFNULL(item_costs.total_cost, 0) AS total_cost,
    -- Lợi nhuận gộp chuẩn = Doanh thu (total_amount) - Tổng COGS thực tế (đã nuốt rác thập phân)
    (i.total_amount - IFNULL(item_costs.total_cost, 0)) AS gross_profit
FROM invoices i
LEFT JOIN (
    -- Lấy trực tiếp snapshot cột total_cogs_amount gánh rác kế toán
    SELECT
        invoice_id,
        SUM(total_cogs_amount) AS total_cost
    FROM invoice_items
    GROUP BY invoice_id
) item_costs ON i.id = item_costs.invoice_id
WHERE i.status = 'COMPLETED';

-- View Thống kê Doanh số Sản phẩm
-- Mục đích: Tổng hợp số lượng bán ra và doanh thu thu được theo từng sản phẩm và theo từng ngày.
-- Ứng dụng UI: Phục vụ cho biểu đồ Top 5 sản phẩm bán chạy.
CREATE OR REPLACE VIEW vw_report_product_sales AS
SELECT 
    DATE(i.created_at) AS sale_date,
    ii.product_id,
    p.sku AS product_sku,
    p.name AS product_name,
    u.name AS unit_name,
    SUM(ii.quantity) AS total_quantity,
    SUM(ii.total_price) AS total_revenue
FROM invoice_items ii
JOIN invoices i ON ii.invoice_id = i.id
JOIN products p ON ii.product_id = p.id
JOIN units u ON ii.unit_id = u.id
WHERE i.status = 'COMPLETED'
GROUP BY DATE(i.created_at), ii.product_id, p.sku, p.name, u.name;

-- View Lịch sử Giao dịch Hóa đơn
-- Mục đích: Chuẩn hóa dữ liệu hiển thị và thực hiện chuyển đổi ngôn ngữ (Mapping) cho hình thức thanh toán ngay tại tầng Database.
-- Ứng dụng UI: Đổ dữ liệu trực tiếp vào bảng Lịch sử giao dịch hóa đơn
CREATE OR REPLACE VIEW vw_report_transaction_history AS
SELECT 
    code AS invoice_code,
    created_at,
    total_amount,
    CASE 
        WHEN payment_method = 'CASH' THEN 'Tiền mặt'
        WHEN payment_method = 'TRANSFER' THEN 'Chuyển khoản'
        ELSE payment_method
    END AS payment_method_text
FROM invoices
WHERE status = 'COMPLETED';


-- View Báo cáo Giá trị Tồn kho
-- Mục đích: Kết nối thông tin tồn kho hiện tại với danh mục sản phẩm và đơn vị tính cơ bản.
-- Ứng dụng UI: Phục vụ cho thẻ KPI Giá trị tồn kho và hiển thị dữ liệu lên bảng Báo cáo giá trị tồn kho hiện tại
CREATE OR REPLACE VIEW vw_report_inventory_valuation AS
SELECT 
    p.name AS product_name,
    u.name AS unit_name,
    i.quantity AS stock_quantity,
    p.cost_price AS mac_price,
    i.total_value AS total_inventory_value
FROM inventory i
JOIN products p ON i.product_id = p.id
JOIN units u ON p.base_unit_id = u.id;


-- View kiểm toán tích hợp phục vụ cho 8 chỉ số trong báo cáo
CREATE OR REPLACE VIEW vw_report_daily_financial_summary AS
SELECT 
    report_date,
    SUM(total_created) AS total_orders_created,
    SUM(total_completed) AS total_orders_completed,
    SUM(total_cancelled) AS total_orders_cancelled,
    SUM(gross_revenue) AS gross_revenue,
    SUM(cancelled_value) AS cancelled_value,
    SUM(net_revenue) AS net_revenue,
    SUM(total_cogs) AS total_cogs,
    SUM(variance_garbage) AS variance_garbage
FROM (
    /* PHẦN 1: BÓC TÁCH DỮ LIỆU HOÁ ĐƠN THEO NGÀY */
    SELECT 
        DATE(i.created_at) AS report_date,
        COUNT(i.id) AS total_created,
        SUM(CASE WHEN i.status = 'COMPLETED' THEN 1 ELSE 0 END) AS total_completed,
        SUM(CASE WHEN i.status = 'CANCELLED' THEN 1 ELSE 0 END) AS total_cancelled,
        IFNULL(SUM(i.total_amount), 0) AS gross_revenue,
        IFNULL(SUM(CASE WHEN i.status = 'CANCELLED' THEN i.total_amount ELSE 0 END), 0) AS cancelled_value,
        IFNULL(SUM(CASE WHEN i.status = 'COMPLETED' THEN i.total_amount ELSE 0 END), 0) AS net_revenue,
        -- Tối ưu lấy COGS thông qua JOIN với cụm tích hợp sản phẩm
        IFNULL(SUM(CASE WHEN i.status = 'COMPLETED' THEN cogs.invoice_cogs ELSE 0 END), 0) AS total_cogs,
        0 AS variance_garbage
    FROM invoices i
    LEFT JOIN (
        SELECT invoice_id, SUM(total_cogs_amount) AS invoice_cogs
        FROM invoice_items
        GROUP BY invoice_id
    ) cogs ON i.id = cogs.invoice_id
    GROUP BY DATE(i.created_at)
    
    UNION ALL
    
    /* PHẦN 2: LẤY SỐ LIỆU ĐIỀU CHỈNH RÁC KHO THEO NGÀY */
    SELECT 
        DATE(st.created_at) AS report_date,
        0 AS total_created,
        0 AS total_completed,
        0 AS total_cancelled,
        0 AS gross_revenue,
        0 AS cancelled_value,
        0 AS net_revenue,
        0 AS total_cogs,
        IFNULL(SUM(st.variance_amount), 0) AS variance_garbage
    FROM stock_transactions st
    WHERE st.type IN ('DATA_CORRECTION', 'ADJUST_VARIANCE', 'ANOMALY_ADJUSTMENT')
    GROUP BY DATE(st.created_at)
) AS combined_data
GROUP BY report_date;








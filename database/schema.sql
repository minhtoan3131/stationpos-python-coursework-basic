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
    total_amount DECIMAL(12,2),             -- Tổng giá trị phiếu nhập
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

    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (unit_id) REFERENCES units(id)
);

CREATE TABLE stock_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    change_quantity INT,
    type ENUM('IMPORT','SALE','ADJUST','CANCEL'),
    reference_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id)
);


CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    created_at DATETIME,
    total_amount DECIMAL(12,2),
    discount DECIMAL(12,2) DEFAULT 0,
    final_amount DECIMAL(12,2),
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


CREATE TABLE tax_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    apply_year INT UNIQUE NOT NULL,       -- năm áp dụng (để map với cbo_year trên UI)
    threshold_amount DECIMAL(15,2),       -- mức miễn thuế (VD: 1,000,000,000)
    vat_percent DECIMAL(5,2),
    pit_percent DECIMAL(5,2),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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





-- View Tổng hợp Hóa đơn và Lợi nhuận
-- Mục đích: Tính toán chính xác doanh thu, tổng giá vốn (COGS), và lợi nhuận gộp của từng hóa đơn sau khi đã trừ chiết khấu (discount).
-- Ứng dụng UI: Phục vụ trực tiếp cho 3 thẻ KPI (Doanh thu, Lợi nhuận gộp, Số hóa đơn) và biểu đồ Xu hướng doanh thu.
CREATE OR REPLACE VIEW vw_report_invoice_summary AS
SELECT
    i.id AS invoice_id,
    i.code AS invoice_code,
    i.created_at,
    DATE(i.created_at) AS sale_date,
    i.payment_method,
    i.total_amount,
    i.discount,
    i.final_amount AS revenue,
    IFNULL(item_costs.total_cost, 0) AS total_cost,
    -- Lợi nhuận gộp = Giá trị thanh toán cuối cùng - Tổng giá vốn hàng bán
    (i.final_amount - IFNULL(item_costs.total_cost, 0)) AS gross_profit
FROM invoices i
LEFT JOIN (
    -- Tính tổng giá vốn của từng hóa đơn dựa trên giá vốn tại thời điểm bán
    SELECT
        invoice_id,
        SUM(cost_price * quantity) AS total_cost
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
    final_amount,
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









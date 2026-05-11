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
    supplier_id INT,
    base_unit_id INT,
    cost_price DECIMAL(15,4),
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
    status ENUM('COMPLETED','CANCELLED') DEFAULT 'COMPLETED',
    cancel_reason TEXT
);


CREATE TABLE invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT,
    product_id INT,
    unit_id INT,
    quantity INT,
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
    vat_percent DECIMAL(5,2),
    pit_percent DECIMAL(5,2),
    updated_at DATETIME
);

CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_name VARCHAR(255),
    address TEXT,
    phone VARCHAR(20)
);
USE pos_vpp;

-- =========================
-- CATEGORIES
-- =========================

INSERT INTO categories(name)
VALUES
('Bút viết'),
('Tập vở'),
('Giấy in'),
('Dụng cụ học tập'),
('Thiết bị văn phòng');

-- =========================
-- SUPPLIERS
-- =========================

INSERT INTO suppliers(name, phone, address)
VALUES
(
    'Thiên Long',
    '0909123456',
    'TP.HCM'
),
(
    'Hồng Hà',
    '0909222333',
    'Hà Nội'
),
(
    'Deli Việt Nam',
    '0909888777',
    'Đà Nẵng'
);

-- =========================
-- UNITS
-- =========================

INSERT INTO units(name)
VALUES
('Cây'),
('Hộp'),
('Cuốn'),
('Ram'),
('Cái');

-- =========================
-- PRODUCTS
-- =========================

INSERT INTO products (
    sku,
    name,
    barcode,

    category_id,
    supplier_id,

    base_unit_id,

    cost_price,
    retail_price,
    wholesale_price,

    min_stock,

    description,

    is_active
)
VALUES

(
    'SP001',
    'Bút bi Thiên Long TL-027',
    '893500170001',

    1,
    1,

    1,

    3000,
    5000,
    4500,

    20,

    'Bút bi màu xanh',
    TRUE
),

(
    'SP002',
    'Bút chì 2B Thiên Long',
    '893500170002',

    1,
    1,

    1,

    4000,
    7000,
    6500,

    15,

    'Bút chì học sinh',
    TRUE
),

(
    'SP003',
    'Tập học sinh 200 trang',
    '893500170003',

    2,
    2,

    3,

    12000,
    18000,
    17000,

    30,

    'Tập kẻ ngang',
    TRUE
),

(
    'SP004',
    'Giấy A4 Double A',
    '893500170004',

    3,
    3,

    4,

    65000,
    85000,
    80000,

    10,

    'Giấy in A4 70gsm',
    TRUE
),

(
    'SP005',
    'Máy tính Casio FX-570VN',
    '893500170005',

    4,
    3,

    5,

    450000,
    520000,
    500000,

    5,

    'Máy tính học sinh',
    TRUE
);

-- =========================
-- UNIT CONVERSIONS
-- =========================

INSERT INTO unit_conversions (
    product_id,
    from_unit_id,
    to_unit_id,
    ratio
)
VALUES
(
    1,
    1,
    2,
    20
),
(
    2,
    1,
    2,
    12
);

-- =========================
-- INVENTORY
-- =========================

INSERT INTO inventory (
    product_id,
    quantity,
    updated_at
)
VALUES
(
    1,
    120,
    NOW()
),
(
    2,
    80,
    NOW()
),
(
    3,
    50,
    NOW()
),
(
    4,
    35,
    NOW()
),
(
    5,
    12,
    NOW()
);

-- =========================
-- TAX CONFIG
-- =========================

INSERT INTO tax_config (
    vat_percent,
    pit_percent,
    updated_at
)
VALUES
(
    8,
    1.5,
    NOW()
);

-- =========================
-- SETTINGS
-- =========================

INSERT INTO settings (
    shop_name,
    address,
    phone
)
VALUES
(
    'POS MINI STORE',
    'Hà Nội',
    '0909000000'
);
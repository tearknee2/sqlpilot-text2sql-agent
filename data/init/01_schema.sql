CREATE DATABASE IF NOT EXISTS sqlpilot_demo
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE sqlpilot_demo;

-- 门店
CREATE TABLE stores (
  store_id     INT PRIMARY KEY,
  store_name   VARCHAR(64) NOT NULL COMMENT '门店名称',
  city         VARCHAR(32) NOT NULL COMMENT '所在城市',
  region       VARCHAR(32) NOT NULL COMMENT '大区：华东/华北/华南',
  open_date    DATE NOT NULL,
  status       VARCHAR(16) NOT NULL COMMENT 'active / closed'
) COMMENT='门店维度表';

-- 客户
CREATE TABLE customers (
  customer_id   INT PRIMARY KEY,
  customer_name VARCHAR(64) NOT NULL,
  gender        VARCHAR(8) COMMENT 'M / F / NULL 表示未填写',
  city          VARCHAR(32),
  member_level  VARCHAR(16) COMMENT '普通 / 银卡 / 金卡',
  register_date DATE NOT NULL
) COMMENT='客户维度表';

-- 商品
CREATE TABLE products (
  product_id   INT PRIMARY KEY,
  product_name VARCHAR(128) NOT NULL,
  category     VARCHAR(32) NOT NULL COMMENT '品类：数码/家居/食品/服饰',
  brand        VARCHAR(64),
  price        DECIMAL(10,2) COMMENT '当前售价，允许 NULL（历史商品未维护）',
  cost         DECIMAL(10,2) NOT NULL,
  is_active    TINYINT(1) NOT NULL DEFAULT 1
) COMMENT='商品维度表';

-- 订单主表
CREATE TABLE orders (
  order_id     BIGINT PRIMARY KEY,
  store_id     INT NOT NULL,
  customer_id  INT NOT NULL,
  order_date   DATE NOT NULL,
  status       VARCHAR(16) NOT NULL COMMENT 'paid / cancelled / refunded / pending',
  channel      VARCHAR(16) NOT NULL COMMENT '线下 / 小程序 / 第三方',
  amount       DECIMAL(12,2) NOT NULL COMMENT '订单实付金额（注意：列名是 amount，不是 total_amount）',
  created_at   DATETIME NOT NULL,
  INDEX idx_orders_date (order_date),
  INDEX idx_orders_store (store_id),
  INDEX idx_orders_status (status),
  INDEX idx_orders_customer (customer_id)
) COMMENT='订单主表';

-- 订单明细
CREATE TABLE order_items (
  item_id     BIGINT PRIMARY KEY,
  order_id    BIGINT NOT NULL,
  product_id  INT NOT NULL,
  qty         INT NOT NULL,
  unit_price  DECIMAL(10,2) NOT NULL,
  discount    DECIMAL(5,2) COMMENT '折扣率 0~1，NULL 表示无折扣',
  INDEX idx_items_order (order_id),
  INDEX idx_items_product (product_id)
) COMMENT='订单明细表';

-- 退货
CREATE TABLE returns (
  return_id    BIGINT PRIMARY KEY,
  order_id     BIGINT NOT NULL,
  product_id   INT NOT NULL,
  return_date  DATE NOT NULL,
  reason       VARCHAR(64) COMMENT '质量问题 / 七天无理由 / 错发 / 其他',
  refund_amount DECIMAL(12,2) NOT NULL,
  INDEX idx_returns_date (return_date)
) COMMENT='退货记录表';
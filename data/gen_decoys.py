"""Generate 24 decoy tables (DDL only) -> data/init/03_decoy_tables.sql.

Decoy tables exist so G0's schema context is genuinely noisy and
schema linking has measurable headroom (doc §4.1 / §4.5 / ADR-12).
They hold no data; they only exist as DDL + catalog metadata.

Run:  python data/gen_decoys.py
"""
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "init" / "03_decoy_tables.sql"

# 每张表 5–7 列；表名与 6 张业务表形近或主题相近，但语义无关。
DECOY_TABLES = [
    {"name": "suppliers", "comment": "供应商主表（占位，无数据）", "columns": [
        ("supplier_id", "INT PRIMARY KEY"),
        ("supplier_name", "VARCHAR(64) NOT NULL"),
        ("contact_name", "VARCHAR(32)"),
        ("phone", "VARCHAR(32)"),
        ("city", "VARCHAR(32)"),
        ("rating", "DECIMAL(3,2)"),
        ("created_at", "DATETIME NOT NULL"),
    ]},
    {"name": "warehouses", "comment": "仓库主表（占位，无数据）", "columns": [
        ("warehouse_id", "INT PRIMARY KEY"),
        ("warehouse_name", "VARCHAR(64) NOT NULL"),
        ("city", "VARCHAR(32) NOT NULL"),
        ("capacity", "INT"),
        ("manager_name", "VARCHAR(32)"),
        ("opened_at", "DATE NOT NULL"),
    ]},
    {"name": "coupons", "comment": "优惠券（占位，无数据）", "columns": [
        ("coupon_id", "INT PRIMARY KEY"),
        ("code", "VARCHAR(32) NOT NULL"),
        ("discount_type", "VARCHAR(16) NOT NULL"),
        ("discount_value", "DECIMAL(10,2) NOT NULL"),
        ("valid_from", "DATE NOT NULL"),
        ("valid_to", "DATE NOT NULL"),
        ("max_uses", "INT"),
    ]},
    {"name": "shipments", "comment": "发货单（占位，无数据）", "columns": [
        ("shipment_id", "BIGINT PRIMARY KEY"),
        ("order_id", "BIGINT NOT NULL"),
        ("warehouse_id", "INT NOT NULL"),
        ("shipped_at", "DATETIME NOT NULL"),
        ("arrived_at", "DATETIME"),
        ("carrier", "VARCHAR(32)"),
        ("tracking_no", "VARCHAR(64)"),
    ]},
    {"name": "inventory", "comment": "库存（占位，无数据）", "columns": [
        ("inventory_id", "BIGINT PRIMARY KEY"),
        ("warehouse_id", "INT NOT NULL"),
        ("product_id", "INT NOT NULL"),
        ("stock_qty", "INT NOT NULL"),
        ("safety_stock", "INT NOT NULL"),
        ("updated_at", "DATETIME NOT NULL"),
    ]},
    {"name": "brands", "comment": "品牌（占位，无数据）", "columns": [
        ("brand_id", "INT PRIMARY KEY"),
        ("brand_name", "VARCHAR(64) NOT NULL"),
        ("country", "VARCHAR(32)"),
        ("founded_year", "INT"),
        ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
    ]},
    {"name": "categories", "comment": "品类主表（占位，无数据）", "columns": [
        ("category_id", "INT PRIMARY KEY"),
        ("category_name", "VARCHAR(32) NOT NULL"),
        ("parent_id", "INT"),
        ("level", "TINYINT NOT NULL"),
        ("sort_order", "INT"),
    ]},
    {"name": "promotions", "comment": "促销活动（占位，无数据）", "columns": [
        ("promotion_id", "INT PRIMARY KEY"),
        ("promotion_name", "VARCHAR(64) NOT NULL"),
        ("start_date", "DATE NOT NULL"),
        ("end_date", "DATE NOT NULL"),
        ("discount_rate", "DECIMAL(5,2)"),
        ("status", "VARCHAR(16) NOT NULL"),
    ]},
    {"name": "reviews", "comment": "商品评价（占位，无数据）", "columns": [
        ("review_id", "BIGINT PRIMARY KEY"),
        ("order_id", "BIGINT NOT NULL"),
        ("product_id", "INT NOT NULL"),
        ("rating", "TINYINT NOT NULL"),
        ("content", "TEXT"),
        ("reviewed_at", "DATETIME NOT NULL"),
        ("is_anonymous", "TINYINT(1) NOT NULL DEFAULT 0"),
    ]},
    {"name": "members", "comment": "会员卡（占位，无数据）", "columns": [
        ("member_id", "INT PRIMARY KEY"),
        ("customer_id", "INT NOT NULL"),
        ("card_no", "VARCHAR(32) NOT NULL"),
        ("level", "VARCHAR(16) NOT NULL"),
        ("points", "INT NOT NULL DEFAULT 0"),
        ("joined_at", "DATE NOT NULL"),
    ]},
    {"name": "addresses", "comment": "客户地址（占位，无数据）", "columns": [
        ("address_id", "INT PRIMARY KEY"),
        ("customer_id", "INT NOT NULL"),
        ("province", "VARCHAR(32)"),
        ("city", "VARCHAR(32)"),
        ("detail", "VARCHAR(255)"),
        ("is_default", "TINYINT(1) NOT NULL DEFAULT 0"),
    ]},
    {"name": "payments", "comment": "支付流水（占位，无数据）", "columns": [
        ("payment_id", "BIGINT PRIMARY KEY"),
        ("order_id", "BIGINT NOT NULL"),
        ("method", "VARCHAR(16) NOT NULL"),
        ("amount", "DECIMAL(12,2) NOT NULL"),
        ("status", "VARCHAR(16) NOT NULL"),
        ("paid_at", "DATETIME"),
        ("channel", "VARCHAR(32)"),
    ]},
    {"name": "invoices", "comment": "发票（占位，无数据）", "columns": [
        ("invoice_id", "BIGINT PRIMARY KEY"),
        ("order_id", "BIGINT NOT NULL"),
        ("invoice_no", "VARCHAR(32) NOT NULL"),
        ("title", "VARCHAR(64)"),
        ("tax_no", "VARCHAR(32)"),
        ("issued_at", "DATETIME NOT NULL"),
    ]},
    {"name": "refunds", "comment": "退款申请（占位，无数据；注意与 returns 区分）", "columns": [
        ("refund_id", "BIGINT PRIMARY KEY"),
        ("order_id", "BIGINT NOT NULL"),
        ("amount", "DECIMAL(12,2) NOT NULL"),
        ("reason", "VARCHAR(64)"),
        ("status", "VARCHAR(16) NOT NULL"),
        ("requested_at", "DATETIME NOT NULL"),
    ]},
    {"name": "employees", "comment": "员工（占位，无数据）", "columns": [
        ("employee_id", "INT PRIMARY KEY"),
        ("employee_name", "VARCHAR(64) NOT NULL"),
        ("store_id", "INT"),
        ("position", "VARCHAR(32) NOT NULL"),
        ("hire_date", "DATE NOT NULL"),
        ("salary", "DECIMAL(10,2)"),
        ("status", "VARCHAR(16) NOT NULL"),
    ]},
    {"name": "departments", "comment": "部门（占位，无数据）", "columns": [
        ("dept_id", "INT PRIMARY KEY"),
        ("dept_name", "VARCHAR(64) NOT NULL"),
        ("manager_id", "INT"),
        ("headcount", "INT NOT NULL DEFAULT 0"),
        ("budget", "DECIMAL(14,2)"),
    ]},
    {"name": "campaigns", "comment": "营销活动（占位，无数据）", "columns": [
        ("campaign_id", "INT PRIMARY KEY"),
        ("campaign_name", "VARCHAR(64) NOT NULL"),
        ("channel", "VARCHAR(32) NOT NULL"),
        ("budget", "DECIMAL(12,2)"),
        ("start_date", "DATE NOT NULL"),
        ("end_date", "DATE NOT NULL"),
    ]},
    {"name": "logistics", "comment": "物流轨迹（占位，无数据）", "columns": [
        ("logistics_id", "BIGINT PRIMARY KEY"),
        ("shipment_id", "BIGINT NOT NULL"),
        ("status", "VARCHAR(32) NOT NULL"),
        ("location", "VARCHAR(64)"),
        ("event_at", "DATETIME NOT NULL"),
        ("operator", "VARCHAR(32)"),
    ]},
    {"name": "carriers", "comment": "承运商（占位，无数据）", "columns": [
        ("carrier_id", "INT PRIMARY KEY"),
        ("carrier_name", "VARCHAR(64) NOT NULL"),
        ("contact_phone", "VARCHAR(32)"),
        ("service_level", "VARCHAR(16)"),
        ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
    ]},
    {"name": "pricing_rules", "comment": "定价规则（占位，无数据）", "columns": [
        ("rule_id", "INT PRIMARY KEY"),
        ("product_id", "INT NOT NULL"),
        ("rule_type", "VARCHAR(32) NOT NULL"),
        ("discount_rate", "DECIMAL(5,2)"),
        ("effective_from", "DATE NOT NULL"),
        ("effective_to", "DATE"),
    ]},
    {"name": "tax_rates", "comment": "税率（占位，无数据）", "columns": [
        ("tax_id", "INT PRIMARY KEY"),
        ("region", "VARCHAR(32) NOT NULL"),
        ("category", "VARCHAR(32) NOT NULL"),
        ("rate", "DECIMAL(5,4) NOT NULL"),
        ("effective_from", "DATE NOT NULL"),
    ]},
    {"name": "regions", "comment": "大区主表（占位，无数据）", "columns": [
        ("region_id", "INT PRIMARY KEY"),
        ("region_name", "VARCHAR(32) NOT NULL"),
        ("manager", "VARCHAR(64)"),
        ("store_count", "INT NOT NULL DEFAULT 0"),
        ("created_at", "DATETIME NOT NULL"),
    ]},
    {"name": "feedback", "comment": "客户反馈（占位，无数据）", "columns": [
        ("feedback_id", "BIGINT PRIMARY KEY"),
        ("customer_id", "INT"),
        ("type", "VARCHAR(32) NOT NULL"),
        ("content", "TEXT"),
        ("submitted_at", "DATETIME NOT NULL"),
        ("status", "VARCHAR(16) NOT NULL"),
    ]},
    {"name": "notifications", "comment": "通知（占位，无数据）", "columns": [
        ("notification_id", "BIGINT PRIMARY KEY"),
        ("customer_id", "INT NOT NULL"),
        ("channel", "VARCHAR(16) NOT NULL"),
        ("title", "VARCHAR(128)"),
        ("content", "TEXT"),
        ("sent_at", "DATETIME NOT NULL"),
    ]},
]


def render() -> str:
    lines = [
        "-- 24 decoy tables: DDL only, no data (doc §4.1 / §4.5 / ADR-12).",
        "-- Generated by data/gen_decoys.py — do not edit by hand.",
        "USE sqlpilot_demo;",
        "",
    ]
    for t in DECOY_TABLES:
        col_lines = [f"  {cname} {cdef}" for cname, cdef in t["columns"]]
        lines.append(f"CREATE TABLE {t['name']} (")
        lines.append(",\n".join(col_lines))
        lines.append(f") COMMENT='{t['comment']}';")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {len(DECOY_TABLES)} decoy tables -> {OUTPUT}")


if __name__ == "__main__":
    main()
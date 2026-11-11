"""Seed sqlpilot_demo with deterministic mock data.

Run:  python -m data.seed        (from project root)
      python data/seed.py        (also works)

Idempotent: re-running on an already-seeded DB is a no-op.
Fixed seed 20241109 => anyone cloning this repo gets identical rows.
Dirty data is planted on purpose (doc §9.5) — test material, not a bug.
"""
from __future__ import annotations

import os
import random
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import pymysql
from dotenv import load_dotenv

SEED = 20241109
load_dotenv()

DB_CONFIG = dict(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3307")),
    user=os.getenv("SEED_MYSQL_USER", "root"),
    password=os.getenv("SEED_MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "sqlpilot_demo"),
    charset="utf8mb4",
    autocommit=False,
)

# ---------------------------------------------------------------- 基础数据池
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋",
         "艳", "勇", "军", "杰", "娟", "涛", "明", "超", "秀兰", "霞"]
CITIES = ["上海", "北京", "深圳", "杭州"]
BRANDS = ["华为", "小米", "苹果", "海尔", "美的", "格力", "联想", "三星", "雀巢", "伊利"]
CATEGORIES = ["数码", "家居", "食品", "服饰"]


# ---------------------------------------------------------------- 工具函数
def connect_with_retry() -> pymysql.connections.Connection:
    last = None
    for i in range(10):
        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.MySQLError as e:
            last = e
            print(f"[seed] connect failed ({i + 1}/10): {e}; retrying in 3s")
            time.sleep(3)
    raise SystemExit(f"[seed] cannot connect after 10 tries: {last}")


def already_seeded(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders")
        return cur.fetchone()[0] > 0


# ---------------------------------------------------------------- 生成器
def gen_stores(rng: random.Random):
    return [
        (1, "上海南京路店", "上海", "华东", "2020-03-01", "active"),
        (2, "上海徐家汇店", "上海", "华东", "2021-06-15", "active"),
        (3, "北京朝阳店", "北京", "华北", "2019-11-20", "active"),
        (4, "北京中关村店", "北京", "华北", "2022-01-10", "active"),
        (5, "深圳南山店", "深圳", "华南", "2020-08-08", "active"),
        (6, "深圳福田店", "深圳", "华南", "2023-02-14", "active"),
        (7, "杭州西湖店", "杭州", "华东", "2021-09-09", "active"),
        (8, "杭州滨江店", "杭州", "华东", "2020-05-01", "closed"),
    ]


def gen_customers(rng: random.Random, n: int = 300):
    rows = []
    for cid in range(1, n + 1):
        name = rng.choice(SURNAMES) + rng.choice(GIVEN)
        gender = "M" if rng.random() < 0.5 else "F"
        if rng.random() < 0.05:          # 脏点：5% gender 为 NULL
            gender = None
        level = rng.choices(["普通", "银卡", "金卡"], weights=[6, 3, 1])[0]
        reg = date(2020, 1, 1) + timedelta(days=rng.randint(0, 1800))
        rows.append((cid, name, gender, rng.choice(CITIES), level, reg.isoformat()))

    # 脏点：2 组同名不同 ID
    for base in (37, 128):
        rows[base - 1] = rows[base - 1][:1] + (rows[0][1],) + rows[base - 1][2:]
        rows[base] = rows[base][:1] + (rows[0][1],) + rows[base][2:]
    return rows


def gen_products(rng: random.Random, n: int = 120):
    rows = []
    null_price_ids = set(rng.sample(range(1, n + 1), 3))   # 脏点：3 条 price NULL
    for pid in range(1, n + 1):
        cat = CATEGORIES[(pid - 1) % 4]
        name = f"{rng.choice(BRANDS)}{cat}型号{pid:03d}"
        if pid in null_price_ids:
            price = None
            cost = Decimal(rng.randint(50, 800))
        else:
            price = Decimal(rng.randint(10, 5000)) + Decimal("0.99")
            cost = (price * Decimal("0.70")).quantize(Decimal("0.01"))
        rows.append((pid, name, cat, rng.choice(BRANDS),
                     None if price is None else str(price), str(cost),
                     1 if rng.random() < 0.9 else 0))
    return rows


def gen_orders_and_items(rng: random.Random):
    """一次生成 orders + order_items（amount 依赖 items 金额）。"""
    orders, items = [], []
    item_id = 1
    start = date(2024, 1, 1)
    for oid in range(1, 3001):
        store_id = rng.randint(1, 8)
        cust_id = rng.randint(1, 300)
        od = start + timedelta(days=rng.randint(0, 365))
        status = rng.choices(
            ["paid", "cancelled", "refunded", "pending"],
            weights=[70, 15, 10, 5],
        )[0]
        channel = rng.choice(["线下", "小程序", "第三方"])
        created = datetime(od.year, od.month, od.day,
                           rng.randint(8, 22), rng.randint(0, 59))

        # 明细：1-5 行，discount 约 30% NULL（脏点）
        n_items = rng.randint(1, 5)
        total = Decimal("0")
        for _ in range(n_items):
            pid = rng.randint(1, 120)
            qty = rng.randint(1, 5)
            unit = Decimal(rng.randint(10, 3000)) + Decimal("0.99")
            if rng.random() < 0.30:
                disc = None
            else:
                disc = Decimal(str(round(rng.uniform(0.5, 0.95), 2)))
            items.append((item_id, oid, pid, qty, str(unit),
                          None if disc is None else str(disc)))
            item_id += 1
            eff = unit * (Decimal("1") - (disc or Decimal("0")))
            total += eff * qty

        # 少量订单 amount 与明细之和不一致（脏点：约 10%）
        amount = total
        if rng.random() < 0.10:
            amount = (total * Decimal(str(round(rng.uniform(0.97, 1.03), 3)))).quantize(Decimal("0.01"))
        orders.append((oid, store_id, cust_id, od.isoformat(), status,
                       channel, str(amount.quantize(Decimal("0.01"))),
                       created.strftime("%Y-%m-%d %H:%M:%S")))

    # 脏点：随机 5 条 paid 改成大写带空格 'PAID '
    paid_idx = [i for i, o in enumerate(orders) if o[4] == "paid"]
    for i in rng.sample(paid_idx, 5):
        o = list(orders[i])
        o[4] = "PAID "
        orders[i] = tuple(o)
    return orders, items


def gen_returns(rng: random.Random, orders, items, n: int = 150):
    paid_orders = {o[0] for o in orders if o[4] in ("paid", "PAID ") or o[4].strip().lower() == "paid"}
    by_order: dict[int, list] = {}
    for it in items:
        if it[1] in paid_orders:
            by_order.setdefault(it[1], []).append(it)
    eligible = [oid for oid, its in by_order.items()]
    picks = rng.sample(eligible, min(n, len(eligible)))
    rows = []
    for rid, oid in enumerate(picks, start=1):
        it = rng.choice(by_order[oid])
        qty, unit = it[3], Decimal(it[4])
        refund = (unit * qty * Decimal("1.0")).quantize(Decimal("0.01"))
        rdate = date(2024, 1, 1) + timedelta(days=rng.randint(0, 365))
        reason = rng.choice(["质量问题", "七天无理由", "错发", "其他"])
        rows.append((rid, oid, it[2], rdate.isoformat(), reason, str(refund)))
    return rows


# ---------------------------------------------------------------- 主流程
def insert_all(conn, stores, customers, products, orders, items, returns):
    sql = {
        "stores": "INSERT INTO stores VALUES (%s,%s,%s,%s,%s,%s)",
        "customers": "INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s)",
        "products": "INSERT INTO products VALUES (%s,%s,%s,%s,%s,%s,%s)",
        "orders": "INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        "order_items": "INSERT INTO order_items VALUES (%s,%s,%s,%s,%s,%s)",
        "returns": "INSERT INTO returns VALUES (%s,%s,%s,%s,%s,%s)",
    }
    payload = {
        "stores": stores, "customers": customers, "products": products,
        "orders": orders, "order_items": items, "returns": returns,
    }
    with conn.cursor() as cur:
        for table in ("returns", "order_items", "orders",
                      "products", "customers", "stores"):
            cur.executemany(sql[table], payload[table])
            print(f"[seed] {table}: {len(payload[table])} rows")
    conn.commit()


def main() -> None:
    rng = random.Random(SEED)
    conn = connect_with_retry()
    try:
        if already_seeded(conn):
            print("[seed] orders 已有数据，跳过（幂等）。如需重灌：先清空表或 down -v")
            return
        stores = gen_stores(rng)
        customers = gen_customers(rng)
        products = gen_products(rng)
        orders, items = gen_orders_and_items(rng)
        returns = gen_returns(rng, orders, items)
        insert_all(conn, stores, customers, products, orders, items, returns)
        print(f"[seed] done. seed={SEED}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
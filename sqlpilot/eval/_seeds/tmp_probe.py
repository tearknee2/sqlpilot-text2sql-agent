from sqlpilot.tools.executor import MySqlExecutor

ex = MySqlExecutor()

queries = {
    "1. orders 行数": "SELECT COUNT(*) FROM orders",
    "2. status 分布": "SELECT status, COUNT(*) AS n FROM orders GROUP BY status",
    "3. status 的原始形态（看空白）": "SELECT DISTINCT CONCAT('[', status, ']') AS s, COUNT(*) AS n FROM orders GROUP BY status",
    "4. customers 总行数 vs distinct name": "SELECT COUNT(*) AS total, COUNT(DISTINCT customer_name) AS distinct_names FROM customers",
    "5. products.price NULL 数": "SELECT COUNT(*) AS total, COUNT(price) AS not_null, COUNT(*) - COUNT(price) AS nulls FROM products",
    "6. order_items.discount NULL 率": "SELECT COUNT(*) AS total, COUNT(discount) AS not_null FROM order_items",
    "7. stores 城市分布": "SELECT city, COUNT(*) AS n FROM stores GROUP BY city",
    "8. returns 月份分布": "SELECT DATE_FORMAT(return_date, '%Y-%m') AS month, COUNT(*) AS n FROM returns GROUP BY month ORDER BY month",
}

for label, sql in queries.items():
    r = ex.execute(sql)
    print(f"\n=== {label} ===")
    print(f"  SQL: {sql[:80]}")
    print(f"  rows: {r['rows']}")
    if r["error"]:
        print(f"  ERROR: {r['error']}")
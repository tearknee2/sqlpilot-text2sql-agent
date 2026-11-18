from sqlpilot.tools.executor import MySqlExecutor
r = MySqlExecutor().execute("SELECT store_name, city FROM stores WHERE region = '华东'")
print("rows:", r["row_count"])
print("columns:", r["columns"])
print("data:", r["rows"])
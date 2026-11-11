#!/bin/bash
# 创建只读账号 sqlpilot_ro 并授予 sqlpilot_demo 的 SELECT 权限。
# 由 mysql 官方镜像的 init 机制在首次初始化时自动执行。
# 密码从环境变量注入，脚本本身不含明文（doc §9.6）。
set -e

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    CREATE USER IF NOT EXISTS 'sqlpilot_ro'@'%' IDENTIFIED BY '${SQLPILOT_RO_PASSWORD}';
    GRANT SELECT ON sqlpilot_demo.* TO 'sqlpilot_ro'@'%';
    FLUSH PRIVILEGES;
EOSQL
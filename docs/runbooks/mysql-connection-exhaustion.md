# MySQL 测试连接耗尽

仅当 Evidence 显示连接来源为 `ops_fault` 且事件目标为 `db-01` 时，预览 `terminate_fault_db_sessions`。审批后只终止该测试账号连接，复查当前连接数、Java 连接池和 `/api/demo` 健康状态。禁止使用 root 账号批量 KILL 未标记连接。

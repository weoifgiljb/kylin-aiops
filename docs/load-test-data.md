# 压测数据手册

本手册只适用于隔离测试数据库或演示环境，严禁对真实业务数据库执行任何压测数据写入或清理操作。执行脚本前，请确认数据库连接指向专用的隔离环境，并确保使用专用、没有活跃事务的 Session。

## 初始化数据库

压测数据脚本不会创建数据库表。请先执行数据库初始化：

```powershell
python tools/init_database.py --database-url "..."
```

## 写入压测数据

以下命令写入 10,000 条可复现的压测数据：

```powershell
python tools/seed_load_data.py --database-url "..." --confirm-load-data --count 10000 --seed 42 --batch-size 1000
```

写入内容包括四类数据：节点、服务、每个节点的最新遥测快照和事件。脚本不会写入历史遥测、用户、凭据、审批动作或评测数据。

## 清理压测数据

完成测试后，可使用以下命令清理：

```powershell
python tools/seed_load_data.py --database-url "..." --confirm-load-data --purge
```

`--purge` 只清理带有 load 前缀的压测数据；如发现外部关联，脚本会拒绝清理，避免破坏非压测数据。对于 PostgreSQL，清理过程会短暂锁定相关业务表，因此只能在隔离测试库或演示环境中执行。

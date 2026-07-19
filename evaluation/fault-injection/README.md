# 可逆故障注入

脚本只允许在隔离实验环境中以 root 运行。每次调用必须传入由字母、数字、`_`、`-` 组成的实验编号；真值追加写入 `/var/lib/kylin-aiops/faults/<experiment_id>/truth.jsonl`。

六类脚本分别是 `cpu.sh`、`memory.sh`、`disk.sh`、`java-service.sh`、`network.sh`、`mysql-connections.sh`。统一调用格式为 `脚本 inject|recover 实验编号 [受控网卡]`。

安全边界：压力进程最长运行 300 秒；磁盘文件固定在实验目录；服务固定为 `kylin-demo-app.service`；网络规则拒绝覆盖已有 netem 且按实验记录的网卡恢复；数据库连接只允许 `ops_fault` 账号。现场运行前仍须完成快照、容量检查和变更审批。

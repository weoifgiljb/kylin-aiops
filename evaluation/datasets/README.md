# 数据集清单

此目录只提交构建脚本和数据清单，不提交服务器日志、账号、IP 或原始业务数据。输入 JSONL 每行必须包含 `experiment_id`、`observed_at`、`label` 和 `metrics`。`build_windows.py` 只在同一个实验内生成 60 步窗口；训练程序随后按 `experiment_id` 整体切分，避免相邻窗口泄漏。

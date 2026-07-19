# 评测输出

盲测输入为 JSON 数组，每项记录实验真值、模型预测、根因排序、传播边、严重度和修复结果。运行 `generate_report.py` 会同时生成 `report.json`、`metrics.csv` 和 `report.html`，并固化代码版本、模型 SHA-256 与随机种子。目录不预置伪造的达标数字；必须由 120 次独立盲测产生。

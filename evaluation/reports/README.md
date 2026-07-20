# 评测输出

盲测输入为 JSON 数组，每项记录实验真值、模型预测、根因排序、传播边、严重度和修复结果。运行 `generate_report.py` 会同时生成 `report.json`、`metrics.csv` 和 `report.html`，并固化代码版本、模型 SHA-256 与随机种子。目录不预置伪造的达标数字；必须由 120 次独立盲测产生。

本地联调可以先用示例输入生成一份真实计算结果（示例数量不足 120 次，因此状态会是“未通过”）：

```powershell
$env:EVALUATION_REPORT_DIR = ".\evaluation\reports\generated"
.\.venv\Scripts\python.exe evaluation\reports\generate_report.py `
  --trials evaluation\reports\example-trials.json `
  --output-dir evaluation\reports\generated\local-smoke `
  --seed 20260720
```

重启中心 API 后，控制台只会列出 `EVALUATION_REPORT_DIR/<批次>/report.json` 中通过 Schema 校验的报告。目录为空或报告不完整时显示空状态，不会用验收门槛代替实测值。

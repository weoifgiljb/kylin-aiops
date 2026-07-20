# 银河麒麟智能运维 MVP

这是一个证据驱动、人工审批优先的 AIOps MVP 工程，覆盖三节点 `Nginx → Java Demo Service → MySQL` 实验链的遥测、事件、诊断、传播路径、受控修复和评测。

## 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn kylin_aiops_api.main:app --reload
cd apps/web
pnpm install
pnpm dev
```

开发令牌为 `dev-admin-token`、`dev-operator-token`、`dev-viewer-token` 和 `dev-agent-token`，只允许用于本机演示。生产部署必须接入真实身份系统、mTLS 和密钥管理。

## 本机真实数据调试

默认不注入演示节点和演示事件。先在项目根目录启动中心 API；本机 Agent 调试期间不要使用 `--reload`，否则进程重载后需要重新注册 Agent。

```powershell
$env:DEMO_SEED = "false"
$env:MINDIE_BASE_URL = "http://127.0.0.1:11434"
$env:MINDIE_MODEL = "llama3.1:latest"
$env:MINDIE_PROVIDER = "Ollama"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue

.\.venv\Scripts\python.exe -m uvicorn kylin_aiops_api.main:app `
  --host 127.0.0.1 --port 8000
```

新开 PowerShell，注册当前机器并以前台方式运行 Agent：

```powershell
$body = @{
  node_id = "local-live-01"
  hostname = [Environment]::MachineName
  architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
  kylin_version = "Windows-dev-agent"
} | ConvertTo-Json

$enrollment = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/agent/v1/enroll" `
  -Headers @{ Authorization = "Bearer dev-agent-token" } `
  -ContentType "application/json" `
  -Body $body

$env:KYLIN_AIOPS_API_URL = "http://127.0.0.1:8000"
$env:KYLIN_AIOPS_NODE_ID = "local-live-01"
$env:KYLIN_AIOPS_TOKEN = $enrollment.enrollment_token
$env:KYLIN_AIOPS_ACTION_SIGNING_SECRET = "development-action-signing-secret"
$env:KYLIN_AIOPS_INTERVAL_SECONDS = "10"

.\.venv\Scripts\python.exe -m kylin_aiops_agent.main
```

控制台随后显示该机器实时采集的 CPU、内存和磁盘指标。开发存储默认位于 API 进程内存中，API 重启后需要重新注册 Agent；没有真实告警时事件列表为空是正确行为。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
cd apps/web
pnpm test
pnpm lint
pnpm build
```

部署、安全边界、模型和未完成的硬件验收见 [docs/deployment.md](docs/deployment.md) 与 [docs/test-report.md](docs/test-report.md)。项目不会预置虚假的 F1、节点容量或昇腾适配结论。

提交代码前同时遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的真实数据、注释和测试规范。

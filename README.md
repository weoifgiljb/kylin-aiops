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

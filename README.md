# 银河麒麟智能运维管理平台

这是一个面向校内多人测试的 AIOps 工程。中心端使用 FastAPI、React、PostgreSQL 和 Redis，支持真实账号登录、角色权限、资源与事件管理、软删除、乐观锁、审计日志和独立 Agent 凭据。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm install
```

需要管理功能时，请先配置本地 PostgreSQL，并从空库执行迁移和创建管理员。管理员密码由交互提示读取，不会出现在命令历史中。

```powershell
$env:DATABASE_URL = "postgresql+psycopg://kylin_aiops:数据库密码@127.0.0.1:5432/kylin_aiops"
$env:JWT_SECRET = "至少32字节的随机JWT密钥"
$env:AGENT_BOOTSTRAP_TOKEN = "与JWT完全不同的至少32字节随机密钥"
$env:ACTION_SIGNING_SECRET = "至少32字节的随机动作签名密钥"
$env:COOKIE_SECURE = "false"
$env:MINDIE_BASE_URL = "http://127.0.0.1:11434"
$env:MINDIE_MODEL = "llama3.1:latest"
$env:MINDIE_PROVIDER = "Ollama"

.\.venv\Scripts\python.exe tools/init_database.py
.\.venv\Scripts\python.exe tools/create_admin.py --username admin --display-name "系统管理员"
.\.venv\Scripts\python.exe -m uvicorn kylin_aiops_api.main:app --reload
pnpm --filter @kylin-aiops/web dev
```

使用本机 Ollama 时，先执行 `ollama pull llama3.1` 并确认 `ollama serve` 正在运行。`MINDIE_*` 必须和 API 在同一个 PowerShell 窗口中设置；API 启动后可在“系统设置 → 模型状态”确认模型是否真正可达。

`COOKIE_SECURE=false` 仅适合本机 HTTP 开发；校内多人环境强制使用 HTTPS 和安全 Cookie。没有 `DATABASE_URL` 时保留的内存模式只用于单元测试和旧实验链，不得用于多人测试。

配置 `DATABASE_URL` 后，PostgreSQL 是节点、事件、遥测、动作和审计的唯一业务状态源；API 不维护数据库的进程内副本。遥测只覆盖每个节点的最新快照，已审批动作通过按节点隔离的 Redis List 交付。控制台以 15 秒轮询刷新概览和事件，不建立常驻事件流连接。

## 校内部署

1. 复制 `.env.example` 为 `.env`，替换所有密码、密钥和证书绝对路径。
2. 执行 `docker compose -f infra/compose/compose.yml config`，确认没有缺失变量。
3. 执行 `docker compose -f infra/compose/compose.yml up -d --build`。Compose 会先执行 `alembic upgrade head`，成功后才启动 API。
4. 首次运行时交互创建管理员：

```bash
docker compose -f infra/compose/compose.yml run --rm ops-api \
  python tools/create_admin.py --username admin --display-name 系统管理员
```

5. 运行只读 curl 冒烟；CRUD 冒烟只能指向隔离测试库。具体命令见 [API 管理与 curl 手册](docs/api-management.md)。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
pnpm generate:api
pnpm test:web
pnpm lint:web
pnpm build:web
```

部署、安全边界和硬件验收见 [部署手册](docs/deployment.md) 与 [测试报告](docs/test-report.md)。提交代码前同时遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的真实数据、注释和测试规范。

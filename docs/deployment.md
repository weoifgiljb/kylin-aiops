# 校内多人测试部署手册

## 前置条件

- 中心端：Linux x86_64/aarch64、Docker 24+ 与 Compose v2，建议 8 核、16 GB 内存、200 GB 数据盘。
- 数据服务：PostgreSQL 16 和 Redis 7 是校内模式的必要依赖，不能使用进程内存替代。
- TLS：准备校方受信 CA 签发的证书和私钥，私钥仅以只读文件挂载，不提交仓库。
- 节点端：银河麒麟、Python 3.11+、systemd、可访问 journald；故障实验节点额外安装 `stress-ng`、`iproute-tc` 和 MySQL 客户端。
- 昇腾端：与硬件匹配的驱动、固件、CANN 和 MindSpore wheel。未运行 `tools/verify_ascend.py` 时不能声称已使用 NPU。

## 中心端

1. 复制 `.env.example` 为 `.env`，替换数据库口令、三个相互独立的强秘密以及证书绝对路径。
2. 执行 `docker compose -f infra/compose/compose.yml config`。Compose 对缺少的秘密或证书路径会直接报错。
3. 执行 `docker compose -f infra/compose/compose.yml up -d --build`。`migrate` 服务先执行 `alembic upgrade head`，迁移失败时 `ops-api` 不会启动。
4. 首次启动后，执行交互式管理员初始化命令：

```bash
docker compose -f infra/compose/compose.yml run --rm ops-api \
  python tools/create_admin.py --username admin --display-name 系统管理员
```

5. 通过 `https://中心域名/` 访问。80 端口只执行 HTTPS 重定向，443 同源代理前端、`/api/` 和 `/agent/`，不配置宽泛 CORS。
6. 按 [API 管理与 curl 手册](api-management.md) 先做只读检查，再对隔离测试库做 CRUD 冒烟。

`APP_ENV=school_test` 下，API 会校验 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET`、`ACTION_SIGNING_SECRET`、`AGENT_BOOTSTRAP_TOKEN` 和 `COOKIE_SECURE=true`。任一共享依赖或强秘密缺失都会拒绝启动；TLS 文件缺失则由 Nginx 拒绝启动。

## Agent

1. 创建系统用户 `kylin-aiops`，安装 wheel 到 `/opt/kylin-aiops/venv`。
2. 安装 `infra/systemd/wrappers/` 到 `/usr/local/libexec/kylin-aiops/`，属主 root、模式 0755，普通用户不可写。
3. 安装并由 root 审核 `kylin-aiops-agent.sudoers`；用 `visudo -cf` 校验。
4. 从模板创建 `/etc/kylin-aiops/agent.env` 和证书文件，权限 0600。首次注册只使用 `AGENT_BOOTSTRAP_TOKEN`，注册后改用节点独立凭据。
5. 安装 service，执行 `systemctl daemon-reload && systemctl enable --now kylin-aiops-agent`。
6. 断开中心网络再恢复，确认 Agent 自动重连且没有开放监听端口。

## 备份与升级

- 升级前备份 PostgreSQL，并记录当前 Alembic revision。
- 新版本先在同版本测试库执行 `alembic upgrade head` 和 CRUD 冒烟，再升级正式校内测试环境。
- 不使用 `Base.metadata.create_all()` 管理部署 Schema，也不手工修改生产表结构。

## Ascend 训练

```bash
python tools/verify_ascend.py > ascend-evidence.json
python evaluation/datasets/build_windows.py --input telemetry.jsonl --output windows.jsonl
kylin-aiops-train --dataset windows.jsonl --output artifacts/model.ckpt --epochs 30 --seed 42
```

必须保存 `ascend-evidence.json`、训练 manifest、checkpoint SHA-256 和盲测报告。数据至少包含每类 10 次训练实验；验收盲测每类 20 次，随机种子与参数不得复用。

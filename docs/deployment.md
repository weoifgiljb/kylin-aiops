# 部署手册

## 前置条件

- 中心端：Linux x86_64/aarch64、Docker 24+ 与 Compose v2，建议 8 核、16 GB 内存、200 GB 数据盘。
- 节点端：银河麒麟、Python 3.11+、systemd、可访问 journald；故障实验节点额外安装 `stress-ng`、`iproute-tc` 和 MySQL 客户端。
- 昇腾端：与硬件匹配的驱动、固件、CANN 和 MindSpore wheel。禁止在未运行 `tools/verify_ascend.py` 的情况下声称使用了 NPU。
- 实验链：准备经 SHA-256 核验的 OpenTelemetry Java Agent JAR。

## 中心端

1. 复制 `.env.example` 为 `.env`，更换数据库口令和至少 32 字节随机动作签名密钥。
2. 将 OTel Java Agent 放到 `infra/offline/artifacts/opentelemetry-javaagent.jar`。
3. 执行 `docker compose -f infra/compose/compose.yml config` 检查配置。
4. 执行 `docker compose -f infra/compose/compose.yml up -d --build`。
5. 初始化 Schema：`python tools/init_database.py --database-url "$DATABASE_URL"`。
6. 实验链使用 `--profile lab` 启动，访问中心控制台 `http://中心IP:8080`，访问受控链 `http://中心IP:18080/api/demo`。

## Agent

1. 创建系统用户 `kylin-aiops`，安装 wheel 到 `/opt/kylin-aiops/venv`。
2. 安装 `infra/systemd/wrappers/` 到 `/usr/local/libexec/kylin-aiops/`，属主 root、模式 0755，普通用户不可写。
3. 安装并由 root 审核 `kylin-aiops-agent.sudoers`；用 `visudo -cf` 校验。
4. 从模板创建 `/etc/kylin-aiops/agent.env` 和证书文件，权限 0600。
5. 安装 service，执行 `systemctl daemon-reload && systemctl enable --now kylin-aiops-agent`。
6. 断开中心网络再恢复，确认 Agent 自动重连且没有开放监听端口。

## Ascend 训练

```bash
python tools/verify_ascend.py > ascend-evidence.json
python evaluation/datasets/build_windows.py --input telemetry.jsonl --output windows.jsonl
kylin-aiops-train --dataset windows.jsonl --output artifacts/model.ckpt --epochs 30 --seed 42
```

必须保存 `ascend-evidence.json`、训练 manifest、checkpoint SHA-256 和盲测报告。数据至少包含每类 10 次训练实验；验收盲测每类 20 次，随机种子与参数不得复用。

## 离线交付

联网打包机执行 `infra/offline/prepare-bundle.sh`，目标机执行 `infra/offline/install.sh`。安装脚本先校验全部 SHA-256，再以 `--no-index` 安装 wheel 并导入镜像。至少在一台清空缓存且断网的同架构麒麟机器完整重装一次。

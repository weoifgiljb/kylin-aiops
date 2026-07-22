# 大规模压测数据注入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供一个显式确认、可重复执行且可精准清理的数据库压测数据生成器，使节点、服务、遥测快照和事件各达到至少 10,000 条。

**Architecture:** 数据生成逻辑放在 `kylin_aiops_api.load_data`，命令行脚本只负责参数、数据库连接与统计输出。所有生成记录使用 `load-` 前缀；清理按外键依赖逆序进行。

**Tech Stack:** Python 3.11、SQLAlchemy 2、PostgreSQL、SQLite、pytest、Ruff。

---

## 文件结构

- Create: `services/ops-api/src/kylin_aiops_api/load_data.py` — 分批生成和清理逻辑。
- Create: `tools/seed_load_data.py` — 必须显式确认的命令行入口。
- Create: `tests/integration/test_load_data.py` — SQLite 集成测试。
- Create: `docs/load-test-data.md` — 使用与清理手册。
- Modify: `README.md` — 链接压测数据手册。

### Task 1: 先定义数据生成器行为

**Files:**
- Create: `tests/integration/test_load_data.py`
- Create: `services/ops-api/src/kylin_aiops_api/load_data.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/integration/test_load_data.py`，包含下列核心测试；SQLite 数据库由 `Base.metadata.create_all(engine)` 建立。

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from kylin_aiops_api.database import Base, IncidentRow, NodeRow, ServiceRow, TelemetrySnapshotRow
from kylin_aiops_api.load_data import LoadDataConfig, purge_load_data, seed_load_data


def session_for(tmp_path) -> Session:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'load-data.db'}")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_creates_each_required_type(tmp_path) -> None:
    session = session_for(tmp_path)
    assert seed_load_data(session, LoadDataConfig(count=10, seed=42, batch_size=4)) == {
        "nodes": 10, "services": 10, "telemetry": 10, "incidents": 10,
    }
    assert session.scalar(select(func.count()).select_from(NodeRow)) == 10
    assert session.scalar(select(func.count()).select_from(ServiceRow)) == 10
    assert session.scalar(select(func.count()).select_from(TelemetrySnapshotRow)) == 10
    assert session.scalar(select(func.count()).select_from(IncidentRow)) == 10
    assert session.scalar(select(ServiceRow.node_id).limit(1)).startswith("load-node-")
    assert session.scalar(select(IncidentRow.root_node_id).limit(1)).startswith("load-node-")


def test_seed_is_idempotent(tmp_path) -> None:
    session = session_for(tmp_path)
    config = LoadDataConfig(count=10, seed=42, batch_size=3)
    seed_load_data(session, config)
    seed_load_data(session, config)
    assert session.scalar(select(func.count()).select_from(NodeRow)) == 10
    assert session.scalar(select(func.count()).select_from(ServiceRow)) == 10
    assert session.scalar(select(func.count()).select_from(TelemetrySnapshotRow)) == 10
    assert session.scalar(select(func.count()).select_from(IncidentRow)) == 10


def test_purge_preserves_non_load_records(tmp_path) -> None:
    session = session_for(tmp_path)
    session.add(NodeRow(id="real-node-01", hostname="real-node-01", architecture="x86_64", kylin_version="V10", status="online", last_seen_at=datetime.now(UTC), display_name="真实节点", description="", tags=[], enabled=True, version=1, archived_at=None, archived_by=None))
    session.commit()
    seed_load_data(session, LoadDataConfig(count=10, seed=42, batch_size=5))
    assert purge_load_data(session) == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}
    assert session.get(NodeRow, "real-node-01") is not None
    assert session.scalar(select(func.count()).select_from(NodeRow)) == 1


@pytest.mark.parametrize("kwargs", [{"count": 0}, {"batch_size": 0}])
def test_config_rejects_non_positive_sizes(kwargs) -> None:
    with pytest.raises(ValueError):
        LoadDataConfig(**kwargs)
```

- [ ] **Step 2: 确认测试因模块不存在失败**

Run: `python -m pytest tests/integration/test_load_data.py -q`

Expected: FAIL，报错找不到 `kylin_aiops_api.load_data`。

- [ ] **Step 3: 提交测试骨架**

```bash
git add tests/integration/test_load_data.py
git commit -m "test: define load data seeding behavior"
```

### Task 2: 实现分批、幂等的生成与精准清理

**Files:**
- Create: `services/ops-api/src/kylin_aiops_api/load_data.py`
- Test: `tests/integration/test_load_data.py`

- [ ] **Step 1: 实现公开接口**

创建模块并使用以下精确接口：

```python
from dataclasses import dataclass
from sqlalchemy.orm import Session

LOAD_NODE_PREFIX = "load-node-"
LOAD_SERVICE_PREFIX = "load-service-"
LOAD_INCIDENT_PREFIX = "load-inc-"


@dataclass(frozen=True)
class LoadDataConfig:
    count: int = 10_000
    seed: int = 42
    batch_size: int = 1_000

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("count 必须大于 0")
        if self.batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")


def seed_load_data(session: Session, config: LoadDataConfig) -> dict[str, int]:
    ...


def purge_load_data(session: Session) -> dict[str, int]:
    ...
```

每个索引 `index` 都生成 `load-node-{index:06d}`、`load-service-{index:06d}`、`load-inc-{index:06d}`。使用 `session.merge()` 分批写入 `NodeRow`、`ServiceRow`、`TelemetrySnapshotRow`、`IncidentRow`，每 `batch_size` 条提交一次，最后返回四个请求数量。

时间基准固定为 `datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)`；节点状态轮换 `online/online/offline`，架构轮换 `x86_64/aarch64`，服务类型轮换 `nginx/java/mysql`，事件严重度轮换 `low/medium/high/critical`，状态轮换 `open/acknowledged/resolved`。遥测指标仅由 `seed + index` 的取模计算 `cpu_percent`、`memory_percent`、`disk_percent` 和 `load_1m`，不得使用非固定随机数。

`purge_load_data` 先统计，再以 `id.like()` 或 `node_id.like()` 的前缀条件按 `IncidentRow`、`TelemetrySnapshotRow`、`ServiceRow`、`NodeRow` 顺序执行删除，最后只提交一次。不能删除无前缀数据，不创建用户、凭据、动作、评测或历史遥测。

- [ ] **Step 2: 确认测试转绿**

Run: `python -m pytest tests/integration/test_load_data.py -q`

Expected: 5 passed。

- [ ] **Step 3: 运行 Lint 并提交**

Run: `python -m ruff check services/ops-api/src/kylin_aiops_api/load_data.py tests/integration/test_load_data.py`

Expected: 通过。

```bash
git add services/ops-api/src/kylin_aiops_api/load_data.py tests/integration/test_load_data.py
git commit -m "feat: add load data generator"
```

### Task 3: 提供必须确认的命令行入口

**Files:**
- Create: `tools/seed_load_data.py`
- Modify: `tests/integration/test_load_data.py`

- [ ] **Step 1: 写 CLI 拒绝未确认写入的失败测试**

在测试文件追加：

```python
import os
import subprocess
import sys


def test_command_requires_explicit_confirmation(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'command.db'}"
    result = subprocess.run(
        [sys.executable, "tools/seed_load_data.py", "--database-url", database_url],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "services/ops-api/src"},
    )
    assert result.returncode != 0
    assert "--confirm-load-data" in result.stderr
    assert not (tmp_path / "command.db").exists()
```

- [ ] **Step 2: 运行该测试确认失败**

Run: `python -m pytest tests/integration/test_load_data.py::test_command_requires_explicit_confirmation -q`

Expected: FAIL，原因是脚本不存在。

- [ ] **Step 3: 实现参数与连接生命周期**

创建 `tools/seed_load_data.py`。该脚本必须定义 `--database-url`、`--confirm-load-data`、`--count`（默认 10000）、`--seed`（默认 42）、`--batch-size`（默认 1000）和 `--purge`。在创建 `Engine` 前，缺少确认标志时调用：

```python
parser.error("必须显式传入 --confirm-load-data 才能修改数据库")
```

确认后创建 `Engine` 和 `Session`；`--purge` 调用 `purge_load_data(session)`，否则调用 `seed_load_data(session, LoadDataConfig(...))`；`finally` 中执行 `engine.dispose()`，使用 `json.dumps({"mode": mode, "counts": counts}, ensure_ascii=False)` 输出结果。不得调用 `Base.metadata.create_all()` 或 Alembic，数据库必须先由既有迁移初始化。

- [ ] **Step 4: 运行测试、Lint 并提交**

Run: `python -m pytest tests/integration/test_load_data.py -q; python -m ruff check tools/seed_load_data.py tests/integration/test_load_data.py`

Expected: 6 passed，Ruff 通过。

```bash
git add tools/seed_load_data.py tests/integration/test_load_data.py
git commit -m "feat: add guarded load data command"
```

### Task 4: 编写操作手册并完成全量验证

**Files:**
- Create: `docs/load-test-data.md`
- Modify: `README.md`

- [ ] **Step 1: 创建手册**

创建 `docs/load-test-data.md`，内容必须覆盖下列命令与安全说明：

```markdown
# 大规模压测数据

仅对隔离测试库或演示环境执行，禁止将真实业务库连接串用于数据注入。

先执行 `python tools/init_database.py --database-url "..."` 初始化迁移。

python tools/seed_load_data.py --database-url "..." --confirm-load-data --count 10000 --seed 42 --batch-size 1000

python tools/seed_load_data.py --database-url "..." --confirm-load-data --purge
```

说明四类数据分别是节点、服务、最新遥测快照和事件；`--purge` 仅处理 `load-` 前缀；脚本不生成历史遥测、用户、凭据、审批动作或评测结果。

- [ ] **Step 2: 在 README 的“验证”章节后添加链接**

追加：

```markdown
大规模分页和界面性能测试请参见[压测数据手册](docs/load-test-data.md)；仅可对隔离测试数据库执行数据注入。
```

- [ ] **Step 3: 运行全量门禁**

Run: `python -m pytest; python -m ruff check .; pnpm test:web; pnpm lint:web; pnpm build:web; git diff --check`

Expected: 所有命令通过。

- [ ] **Step 4: 提交文档**

```bash
git add docs/load-test-data.md README.md
git commit -m "docs: document load data seeding"
```

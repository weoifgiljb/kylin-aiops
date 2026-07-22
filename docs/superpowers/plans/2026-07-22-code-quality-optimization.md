# 前后端质量与性能优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除生产环境双状态源，修复分页、动作队列和节点标签编辑问题，减少重复请求与无效依赖，并让 OpenAPI 成为前后端唯一类型契约。

**Architecture:** PostgreSQL 是配置 `DATABASE_URL` 时唯一的业务状态源；内存存储仅用于无数据库的单元测试和演示。FastAPI 共享一个 SQLAlchemy engine/session factory，读写通过小型 SQL 存储服务完成；列表查询在数据库分页并批量加载关联数据。前端继续使用现有 React Query 和 Ant Design，不新增状态、请求或图表依赖。

**Tech Stack:** Python 3.11、FastAPI、SQLAlchemy 2、PostgreSQL/SQLite 测试库、Redis、React 19、TypeScript 5.9、TanStack Query、Ant Design、Vitest、pytest。

---

## 实施边界与文件职责

- 新建 `services/ops-api/src/kylin_aiops_api/persistence.py`：唯一负责创建和释放 SQLAlchemy engine/session factory。
- 新建 `services/ops-api/src/kylin_aiops_api/sql_store.py`：数据库模式下的概览、事件、动作、Agent 与遥测读写，不注册路由。
- 新建 `services/ops-api/src/kylin_aiops_api/schemas.py`：公共 API 的 Pydantic 请求、响应和分页模型。
- 新建 `services/ops-api/src/kylin_aiops_api/pagination.py`：复用数据库 `COUNT/OFFSET/LIMIT`，不包含业务筛选。
- `store.py` 只保留内存实现；删除数据库加载、`persist_all()` 和生产持久化职责。
- `management.py` 保留管理路由，但复用分页、响应模型和序列化函数；不再把 `AuthManager` 当数据库容器。
- `main.py` 只负责依赖装配和路由，不直接操作数据库行。
- 前端保留 `api/client.ts` 作为唯一请求入口；`api/types.ts` 只重导出生成类型或定义确实不属于 OpenAPI 的纯 UI 类型。
- 不引入 Repository 基类、通用 CRUD 框架、事件总线或新前端状态库。
- 新增或修改的注释、模块说明和 docstring 全部使用简体中文。

## 公共接口变化

- 所有列表接口正式支持并返回服务端分页：`page`、`page_size`、`items`、`total`。
- 节点、服务列表增加可选 `q` 查询参数，为资源编辑器的远程选择提供搜索。
- OpenAPI 为用户、节点、服务、依赖、事件、审计、概览和动作响应提供具体 schema，不再生成 `{[key: string]: unknown}`。
- SSE `/api/v1/events/stream` 删除；前端使用已有 15 秒 React Query 轮询。
- Redis 动作队列内部由“共享 Stream 扫描”改为“每节点一个 Redis List”；HTTP API 形状不变，继续保持当前原子取走、至多一次交付语义。
- 数据库模式不再暴露或依赖 `InMemoryStore.persist_all()`。

---

### Task 1: 固化双状态源缺陷的回归测试

**Files:**
- Modify: `tests/api/test_management.py`

- [ ] **Step 1: 写入失败的端到端测试**

在现有 `management_client()` 和 `login()` 辅助函数之后添加：

```python
def test_database_incident_is_visible_to_overview_and_diagnosis(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")

    created = client.post(
        "/api/v1/incidents",
        headers=admin,
        json={
            "title": "数据库状态源回归",
            "fault_type": "review",
            "severity": "high",
        },
    )
    incident_id = created.json()["id"]

    overview = client.get("/api/v1/overview", headers=admin)
    diagnosis = client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers=admin)

    assert created.status_code == 201
    assert overview.json()["active_incidents"] == 1
    assert diagnosis.status_code == 200
    assert diagnosis.json()["source"] == "pending"
```

- [ ] **Step 2: 运行测试并确认当前缺陷**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_management.py::test_database_incident_is_visible_to_overview_and_diagnosis -v`

Expected: FAIL；概览返回 `active_incidents == 0`，诊断返回 404。

- [ ] **Step 3: 提交只含回归测试的变更**

```bash
git add tests/api/test_management.py
git commit -m "test: 固化数据库与概览状态一致性要求"
```

---

### Task 2: 建立单一数据库 engine 与认证查询入口

**Files:**
- Create: `services/ops-api/src/kylin_aiops_api/persistence.py`
- Modify: `services/ops-api/src/kylin_aiops_api/auth.py`
- Modify: `services/ops-api/src/kylin_aiops_api/main.py`
- Modify: `tools/export_openapi.py`
- Test: `tests/api/test_management.py`

- [ ] **Step 1: 增加共享连接池测试**

```python
def test_database_mode_shares_one_session_factory(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    app = client.app

    assert app.state.auth_manager.sessions is app.state.database.sessions
```

- [ ] **Step 2: 运行新测试并确认失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_management.py::test_database_mode_shares_one_session_factory -v`

Expected: FAIL，`app.state.database` 尚不存在。

- [ ] **Step 3: 新建共享数据库容器**

`persistence.py` 的公开接口固定如下：

```python
"""集中管理数据库连接池和会话工厂，避免同一进程重复创建 engine。"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        self.sessions: sessionmaker[Session] = sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    def dispose(self) -> None:
        self.engine.dispose()
```

- [ ] **Step 4: 让 `AuthManager` 接收 session factory**

将构造函数改为：

```python
def __init__(
    self,
    sessions: sessionmaker[Session],
    jwt_secret: str,
    redis_client: Any | None = None,
) -> None:
    if len(jwt_secret.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET 至少需要 32 字节")
    self.sessions = sessions
    self.jwt_secret = jwt_secret
    self.passwords = PasswordHash.recommended()
    self.limiter = LoginRateLimiter(redis_client)
```

`seed_admin()` 使用局部 `Database`，并在 `finally` 中 `dispose()`，不再直接调用 `create_engine()`。

- [ ] **Step 5: 统一人类令牌和 Agent 令牌的识别顺序**

在 `AuthManager` 增加：

```python
def authenticate_bearer(self, token: str) -> AuthUser:
    """JWT 直接走用户校验，非 JWT 才查询 Agent 凭证，避免每个人类请求多查一次表。"""

    if token.count(".") == 2:
        return self.current_user(token)
    agent = self.current_agent(token)
    if agent is None:
        raise ApiProblem(401, "INVALID_TOKEN", "访问令牌无效")
    return agent
```

`main.py::current_user()` 保留 bootstrap token 比较，然后只调用 `manager.authenticate_bearer(token)`；删除先查 `current_agent()` 再查 `current_user()` 的分支。

- [ ] **Step 6: 在 `create_app()` 中只创建一个 `Database`**

数据库模式固定装配为：

```python
database = Database(configured_database_url) if configured_database_url else None
app.state.database = database
app.state.auth_manager = (
    AuthManager(database.sessions, configured_secret, redis_client=redis_client)
    if database is not None
    else None
)
```

`tools/export_openapi.py` 最后只调用 `app.state.database.dispose()`。

- [ ] **Step 7: 运行认证和管理测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_management.py tests/api/test_api.py -q`

Expected: PASS；共享 session factory 测试通过，登录、刷新和 Agent 凭证行为不变。

- [ ] **Step 8: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/persistence.py services/ops-api/src/kylin_aiops_api/auth.py services/ops-api/src/kylin_aiops_api/main.py tools/export_openapi.py tests/api/test_management.py
git commit -m "refactor: 统一数据库连接池与令牌查询入口"
```

---

### Task 3: 让概览、事件、诊断和告警直接使用数据库

**Files:**
- Create: `services/ops-api/src/kylin_aiops_api/sql_store.py`
- Create: `services/ops-api/src/kylin_aiops_api/serializers.py`
- Create: `services/ops-api/src/kylin_aiops_api/schemas.py`
- Modify: `services/ops-api/src/kylin_aiops_api/store.py`
- Modify: `services/ops-api/src/kylin_aiops_api/main.py`
- Modify: `services/ops-api/src/kylin_aiops_api/management.py`
- Test: `tests/api/test_management.py`

- [ ] **Step 1: 先移动跨模块请求模型**

把 `Enrollment`、`ActionResult`、`Alert` 和 `AlertWebhook` 从 `main.py` 移到 `schemas.py`；`main.py` 与 `sql_store.py` 都从 `schemas.py` 导入，避免存储层反向依赖应用入口。定义固定为：

```python
class Enrollment(BaseModel):
    node_id: str
    hostname: str
    architecture: str
    kylin_version: str


class ActionResult(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    health_check: Literal["passed", "failed"]


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    fingerprint: str = Field(min_length=1)


class AlertWebhook(BaseModel):
    status: Literal["firing", "resolved"]
    alerts: list[Alert]
```

- [ ] **Step 2: 提取事件序列化函数**

`serializers.py` 定义 `_dt()`、`serialize_node()`、`serialize_service()`、`serialize_dependency()`、`serialize_user()`、`serialize_audit()` 和：

```python
def serialize_incident(
    row: IncidentRow,
    evidence_rows: list[EvidenceRow],
    diagnosis: DiagnosisRow | None,
) -> dict[str, Any]:
    """把已批量加载的数据库行转换为稳定的事件响应，序列化阶段不再发起查询。"""

    evidence = [
        {
            "id": item.id,
            "kind": item.kind,
            "node_id": item.node_id,
            "summary": item.summary,
            "observed_at": _dt(item.observed_at),
        }
        for item in evidence_rows
    ]
    diagnosis_data = {
        "summary": diagnosis.summary if diagnosis else "等待诊断",
        "root_cause": diagnosis.root_cause if diagnosis else row.root_node_id or "",
        "severity": diagnosis.severity if diagnosis else row.severity,
        "propagation_path": diagnosis.propagation_path if diagnosis else [],
        "evidence_refs": diagnosis.evidence_refs if diagnosis else [],
        "recommended_steps": diagnosis.recommended_steps if diagnosis else [],
        "action_candidates": diagnosis.action_candidates if diagnosis else [],
        "confidence": diagnosis.confidence if diagnosis else 0.0,
        "source": diagnosis.source if diagnosis else "pending",
    }
    return {
        "id": row.id,
        "title": row.title,
        "fault_type": row.fault_type,
        "severity": row.severity,
        "status": row.status,
        "source": row.source,
        "started_at": _dt(row.started_at),
        "ended_at": _dt(row.ended_at),
        "root_node": row.root_node_id,
        "assignee_user_id": row.assignee_user_id,
        "handling_notes": row.handling_notes,
        "version": row.version,
        "archived_at": _dt(row.archived_at),
        "propagation_path": diagnosis_data["propagation_path"],
        "evidence": evidence,
        "diagnosis": diagnosis_data,
    }
```

- [ ] **Step 3: 实现数据库状态服务的事件读取**

`SqlControlPlaneStore` 构造函数只接收 `sessionmaker` 和动作队列。事件读取使用三条有界查询：事件、该事件证据、该事件诊断。

```python
class SqlControlPlaneStore:
    def __init__(self, sessions: sessionmaker[Session], action_queue: ActionQueue) -> None:
        self.sessions = sessions
        self.action_queue = action_queue

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            row = session.get(IncidentRow, incident_id)
            if row is None:
                return None
            evidence = list(
                session.scalars(select(EvidenceRow).where(EvidenceRow.incident_id == incident_id))
            )
            diagnosis = session.scalar(
                select(DiagnosisRow).where(DiagnosisRow.incident_id == incident_id)
            )
            return serialize_incident(row, evidence, diagnosis)
```

- [ ] **Step 4: 实现数据库概览**

`overview()` 使用聚合查询计算在线节点、节点总数、活跃事件、今日告警和待审批动作；节点列表只查未归档节点，拓扑从 `DependencyEdgeRow + ServiceRow` 得出。禁止读取启动时缓存。

关键聚合形状：

```python
active_incidents = session.scalar(
    select(func.count()).select_from(IncidentRow).where(
        IncidentRow.status.in_(("open", "acknowledged", "resolving")),
        IncidentRow.archived_at.is_(None),
    )
) or 0
```

- [ ] **Step 5: 把告警接收改为数据库幂等 upsert**

事件 ID 继续使用 `inc-{fingerprint}`，因此不新增映射表。每条告警在同一事务内 `session.get()`；不存在则创建，存在则只更新状态。一次 webhook 只提交一次事务。

- [ ] **Step 6: 路由改为依赖存储方法**

`main.py` 中 `overview()`、`receive_alerts()`、`run_diagnosis()` 和 `chat()` 不再访问 `.incidents` 字典；统一调用 `get_incident()`、`overview()` 和 `receive_alerts()`。无数据库模式仍使用 `InMemoryStore` 的同名方法。

`create_app()` 的存储装配固定为：

```python
action_queue: ActionQueue = (
    RedisStreamActionQueue.from_url(redis_url) if redis_url else InMemoryActionQueue()
)
app.state.store = (
    SqlControlPlaneStore(database.sessions, action_queue)
    if database is not None
    else InMemoryStore(seed_demo=seed_demo, action_queue=action_queue)
)
```

`store.py` 增加 `ControlPlaneStore` Protocol，Task 3 先声明 `overview()`、`get_incident()` 和 `receive_alerts()`；Task 4 再补齐动作、Agent、遥测和审计方法。FastAPI 依赖函数返回 `ControlPlaneStore`，不再标注为具体 `InMemoryStore`。

`register_management_routes()` 新增独立的 `sessions: sessionmaker[Session]` 参数，内部所有 `with auth.sessions()` 改为 `with sessions()`；`AuthManager` 只负责认证。`create_app()` 传入 `database.sessions`。

- [ ] **Step 7: 复用序列化并删除查询型 `_incident()`**

`management.py` 导入 `serializers.py`，删除文件尾部重复的响应转换函数。详情接口显式查询关联行后调用 `serialize_incident()`，序列化函数本身不得访问 session。

- [ ] **Step 8: 运行回归测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_management.py::test_database_incident_is_visible_to_overview_and_diagnosis tests/api/test_management.py::test_operator_manages_manual_incident_but_cannot_rewrite_alert -v`

Expected: PASS；新建事件立即出现在概览并可诊断，告警字段保护不变。

- [ ] **Step 9: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/sql_store.py services/ops-api/src/kylin_aiops_api/serializers.py services/ops-api/src/kylin_aiops_api/schemas.py services/ops-api/src/kylin_aiops_api/store.py services/ops-api/src/kylin_aiops_api/main.py services/ops-api/src/kylin_aiops_api/management.py tests/api/test_management.py
git commit -m "refactor: 以数据库作为事件与概览唯一状态源"
```

---

### Task 4: 遥测、动作和审计改为增量持久化

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/database.py`
- Create: `migrations/versions/0002_telemetry_snapshots.py`
- Modify: `services/ops-api/src/kylin_aiops_api/sql_store.py`
- Modify: `services/ops-api/src/kylin_aiops_api/store.py`
- Modify: `services/ops-api/src/kylin_aiops_api/main.py`
- Modify: `services/diagnosis-worker/src/kylin_aiops_diagnosis/mcp_server.py`
- Delete: `tests/integration/test_persistent_store.py`
- Create: `tests/integration/test_sql_store.py`

- [ ] **Step 1: 写入“遥测不覆盖管理字段”的失败测试**

```python
def test_telemetry_updates_only_observed_node_fields(sql_store, sessions) -> None:
    with sessions() as session:
        session.add(
            NodeRow(
                id="node-01",
                hostname="node-01",
                status="offline",
                display_name="教学楼节点",
                description="保留管理描述",
                tags=["教学楼"],
                enabled=True,
                version=1,
            )
        )
        session.commit()

    sql_store.record_telemetry(
        "node-01",
        datetime(2026, 7, 22, tzinfo=UTC),
        {"cpu_percent": 12.0},
    )

    with sessions() as session:
        node = session.get(NodeRow, "node-01")
        assert node.display_name == "教学楼节点"
        assert node.description == "保留管理描述"
        assert node.tags == ["教学楼"]
```

- [ ] **Step 2: 新增遥测快照表与迁移**

模型固定为：

```python
class TelemetrySnapshotRow(Base):
    __tablename__ = "telemetry_snapshots"
    node_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON)
```

迁移 `0002_telemetry_snapshots.py` 固定使用 `revision = "0002_telemetry_snapshots"`、`down_revision = "0001_initial"`。由于现有 `0001_initial` 动态调用当前 `Base.metadata.create_all()`，`upgrade()` 必须先执行 `inspect(op.get_bind()).has_table("telemetry_snapshots")`：表不存在才创建表和索引，已存在则不重复创建；`downgrade()` 使用同样检查后删除表。这样同时兼容已经执行过 0001 的数据库和从空库执行全部迁移的数据库，不修改既有迁移历史。

- [ ] **Step 3: 实现精确写入方法**

`SqlControlPlaneStore` 增加以下精确写入方法，每个方法只修改对应行并自行控制一个事务：

```python
def enroll_node(self, payload: Enrollment) -> None:
    with self.sessions() as session:
        row = session.get(NodeRow, payload.node_id)
        if row is None:
            row = NodeRow(
                id=payload.node_id,
                display_name=payload.hostname,
                description="",
                tags=[],
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
            session.add(row)
        row.hostname = payload.hostname
        row.architecture = payload.architecture
        row.kylin_version = payload.kylin_version
        row.status = "online"
        session.commit()

def record_telemetry(
    self,
    node_id: str,
    observed_at: datetime,
    metrics: dict[str, float],
) -> None:
    with self.sessions() as session:
        row = session.get(NodeRow, node_id)
        if row is None:
            raise KeyError(node_id)
        row.status = "online"
        row.last_seen_at = observed_at
        session.merge(
            TelemetrySnapshotRow(
                node_id=node_id,
                observed_at=observed_at,
                metrics=metrics,
            )
        )
        session.commit()

def create_action(self, action: ActionRequest, actor_id: str) -> None:
    with self.sessions() as session:
        session.add(_action_row(action))
        session.add(_audit_row(actor_id, "action.previewed", action.id))
        session.commit()

def get_action(self, action_id: str) -> ActionRequest | None:
    with self.sessions() as session:
        row = session.get(ActionRequestRow, action_id)
        return _action_from_row(row) if row is not None else None

def save_approved_action(self, action: ActionRequest, actor_id: str) -> None:
    with self.sessions() as session:
        row = session.get(ActionRequestRow, action.id, with_for_update=True)
        if row is None:
            raise KeyError(action.id)
        row.status = action.status.value
        row.approved_by = action.approved_by
        row.approved_at = action.approved_at
        session.add(
            _audit_row(
                actor_id,
                "action.approved",
                action.id,
                {"node_id": action.node_id},
            )
        )
        session.commit()

def record_action_result(self, action_id: str, result: ActionResult) -> None:
    with self.sessions() as session:
        row = session.get(ActionRequestRow, action_id, with_for_update=True)
        if row is None:
            raise KeyError(action_id)
        session.merge(
            ActionExecutionRow(
                id=f"exec-{action_id}",
                action_request_id=action_id,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                health_check_passed=result.health_check == "passed",
                executed_at=datetime.now(UTC),
            )
        )
        row.status = ActionStatus.EXECUTED.value
        session.commit()

def append_audit(
    self,
    actor_id: str,
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
) -> None:
    with self.sessions() as session:
        session.add(_audit_row(actor_id, action, target, details))
        session.commit()
```

同文件实现 `_action_row()`、`_action_from_row()` 和 `_audit_row()` 三个纯转换函数；它们只在 ORM 行、`ActionRequest` 和审计字段之间转换，不打开 session。所有未找到错误由路由转换为现有 `ApiProblem` code。

- [ ] **Step 4: 路由切换到增量方法**

`preview_action()`、`approve_action()`、`enroll_agent()`、`ingest_telemetry()` 和 `action_result()` 调用上述方法；删除所有 `persist_all()` 调用。

- [ ] **Step 5: 把内存存储收缩为测试实现**

从 `InMemoryStore` 删除 `database_url`、`engine`、`_load_database()` 和 `persist_all()`。为 Task 3/4 的存储方法提供纯内存实现，使既有无数据库 API 测试继续运行。

`mcp_server.py::main()` 仍显式使用 `InMemoryStore(seed_demo=True)`，不自动连接生产数据库。

- [ ] **Step 6: 用 SQL 存储测试替换旧的全量持久化测试**

删除 `test_store_reloads_nodes_and_incidents_from_database()`，新增 `test_sql_store.py` 覆盖：事件创建后立即读取、遥测只更新目标节点、动作结果只写一条执行记录。

- [ ] **Step 7: 验证迁移和接口**

Run: `./.venv/Scripts/python.exe -m pytest tests/integration/test_migrations.py tests/integration/test_sql_store.py tests/api/test_api.py -q`

Expected: PASS；迁移可升级/降级，数据库模式不存在全量持久化路径。

- [ ] **Step 8: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/database.py migrations/versions/0002_telemetry_snapshots.py services/ops-api/src/kylin_aiops_api/sql_store.py services/ops-api/src/kylin_aiops_api/store.py services/ops-api/src/kylin_aiops_api/main.py services/diagnosis-worker/src/kylin_aiops_diagnosis/mcp_server.py tests/integration/test_sql_store.py tests/integration/test_persistent_store.py
git commit -m "refactor: 将遥测与动作改为增量持久化"
```

---

### Task 5: 使用数据库原生分页并消除事件 N+1 查询

**Files:**
- Create: `services/ops-api/src/kylin_aiops_api/pagination.py`
- Modify: `services/ops-api/src/kylin_aiops_api/management.py`
- Test: `tests/api/test_management.py`

- [ ] **Step 1: 写入分页边界测试**

创建 25 个用户后请求第一页和第二页，断言第一页 20 条、第二页 5 条、`total == 26`（包含管理员）且两页 ID 不重复。

```python
first = client.get("/api/v1/admin/users?page=1&page_size=20", headers=admin).json()
second = client.get("/api/v1/admin/users?page=2&page_size=20", headers=admin).json()
assert len(first["items"]) == 20
assert len(second["items"]) == 6
assert first["total"] == 26
assert {item["id"] for item in first["items"]}.isdisjoint(
    item["id"] for item in second["items"]
)
```

- [ ] **Step 2: 新建分页辅助函数**

```python
@dataclass(frozen=True)
class PageRows(Generic[T]):
    items: list[T]
    total: int


def page_scalars(
    session: Session,
    statement: Select[tuple[T]],
    page: int,
    page_size: int,
) -> PageRows[T]:
    total_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(session.scalar(total_statement) or 0)
    items = list(
        session.scalars(statement.offset((page - 1) * page_size).limit(page_size))
    )
    return PageRows(items, total)
```

- [ ] **Step 3: 替换六个全表加载列表**

用户、审计、节点、服务、依赖和事件列表都先完成筛选/排序，再调用 `page_scalars()`。响应通过：

```python
def page_response(items: list[dict[str, Any]], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {"items": items, "total": total, "page": page, "page_size": page_size}
```

删除接收完整列表后再切片的 `_page()`。

节点列表增加 `q` 并使用 `or_(NodeRow.id.contains(q), NodeRow.display_name.contains(q))`；服务列表增加 `q` 并使用 `or_(ServiceRow.id.contains(q), ServiceRow.name.contains(q))`。空字符串不添加筛选条件。

- [ ] **Step 4: 批量加载当前页事件关联数据**

先得到当前页 `incident_ids`，再各执行一条 `IN` 查询加载证据与诊断，构造两个映射后序列化：

```python
evidence_by_incident: dict[str, list[EvidenceRow]] = defaultdict(list)
for evidence in session.scalars(
    select(EvidenceRow).where(EvidenceRow.incident_id.in_(incident_ids))
):
    evidence_by_incident[evidence.incident_id].append(evidence)

diagnosis_by_incident = {
    diagnosis.incident_id: diagnosis
    for diagnosis in session.scalars(
        select(DiagnosisRow).where(DiagnosisRow.incident_id.in_(incident_ids))
    )
}
```

空页不执行 `IN ()` 查询，直接返回空 `items`。

- [ ] **Step 5: 增加查询次数测试**

通过 SQLAlchemy `event.listen(engine, "before_cursor_execute", callback)` 统计事件列表查询；20 条事件的列表请求不超过 4 条业务 SQL：总数、事件页、证据、诊断。认证 SQL 在获取 token 后开始计数。

- [ ] **Step 6: 运行测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_management.py -q`

Expected: PASS；第二页可访问，事件页查询数不随事件数量增长。

- [ ] **Step 7: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/pagination.py services/ops-api/src/kylin_aiops_api/management.py tests/api/test_management.py
git commit -m "perf: 使用数据库分页并批量加载事件关联数据"
```

---

### Task 6: 用每节点 Redis List 替换共享 Stream 扫描

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/queue.py`
- Modify: `tests/integration/test_action_queue.py`

- [ ] **Step 1: 写入超过 100 条其他节点动作的回归测试**

测试使用一个实现 `rpush/lpop` 的最小内存 Redis stub；先放入 150 条 `node-a` 动作，再放入一条 `node-b` 动作，断言 `node-b` 一次即可取到自己的动作。

```python
for index in range(150):
    queue.enqueue(envelope(f"a-{index}", "node-a"))
queue.enqueue(envelope("target", "node-b"))

selected = queue.dequeue("node-b")
assert selected is not None
assert selected.action_id == "target"
```

- [ ] **Step 2: 将队列键改为节点专属 List**

```python
class RedisActionQueue:
    prefix = "kylin-aiops:approved-actions"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @classmethod
    def from_url(cls, url: str) -> "RedisActionQueue":
        return cls(Redis.from_url(url, decode_responses=True))

    def _key(self, node_id: str) -> str:
        return f"{self.prefix}:{node_id}"

    def enqueue(self, envelope: ActionEnvelope) -> None:
        self.redis.rpush(self._key(envelope.node_id), _serialize(envelope))

    def dequeue(self, node_id: str) -> ActionEnvelope | None:
        payload = self.redis.lpop(self._key(node_id))
        return _deserialize(payload) if payload is not None else None
```

保留 `RedisStreamActionQueue` 名称会误导维护者，因此类重命名为 `RedisActionQueue`，同步修改 `main.py` import。HTTP 行为不变。

- [ ] **Step 3: 测试原子消费行为**

同一节点只有一条动作时连续调用两次 `dequeue()`，第一次返回动作、第二次返回 `None`。这验证 Redis `LPOP` 的原子取走语义，删除 `XRANGE + XDEL` 的竞态窗口。

- [ ] **Step 4: 运行队列测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/integration/test_action_queue.py tests/api/test_api.py -q`

Expected: PASS；不存在 100 条扫描上限。

- [ ] **Step 5: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/queue.py services/ops-api/src/kylin_aiops_api/main.py tests/integration/test_action_queue.py
git commit -m "perf: 使用节点专属 Redis 动作队列"
```

---

### Task 7: 让 OpenAPI 成为唯一前后端类型契约

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/schemas.py`
- Modify: `services/ops-api/src/kylin_aiops_api/main.py`
- Modify: `services/ops-api/src/kylin_aiops_api/management.py`
- Modify: `services/ops-api/openapi.json`
- Modify: `packages/api-client/src/schema.ts`
- Modify: `apps/web/src/api/types.ts`
- Modify: `apps/web/src/api/client.ts`
- Test: `tests/api/test_openapi_contract.py`

- [ ] **Step 1: 扩展 OpenAPI 合约测试**

```python
def test_public_list_responses_have_concrete_item_schemas() -> None:
    document = build_openapi_document()
    response = document["paths"]["/api/v1/incidents"]["get"]["responses"]["200"]
    schema = response["content"]["application/json"]["schema"]

    assert schema["$ref"].endswith("/IncidentPage")
    assert "IncidentResponse" in document["components"]["schemas"]
```

- [ ] **Step 2: 定义具体响应模型**

`schemas.py` 定义 `UserResponse`、`NodeResponse`、`ServiceResponse`、`DependencyResponse`、`EvidenceResponse`、`DiagnosisResponse`、`IncidentResponse`、`AuditLogResponse`、`OverviewResponse`、`ActionResponse`，以及显式命名的分页模型：

```python
class IncidentPage(BaseModel):
    items: list[IncidentResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
```

同时逐一声明 `UserPage`、`NodePage`、`ServicePage`、`DependencyPage` 和 `AuditLogPage`；每个模型都包含 `items: list[对应 Response]`、`total: int`、`page: int`、`page_size: int` 四个字段。不使用会生成不稳定名称的匿名泛型 schema。

- [ ] **Step 3: 给全部公共路由添加 `response_model`**

路由与响应模型映射锁定如下：

- `GET /api/v1/admin/users` → `UserPage`；用户创建、更新、重置密码、归档、恢复 → `UserResponse`。
- `GET /api/v1/resources/nodes` → `NodePage`；节点创建、更新、归档、恢复 → `NodeResponse`。
- `GET /api/v1/resources/services` → `ServicePage`；服务创建、更新、归档、恢复 → `ServiceResponse`。
- `GET /api/v1/resources/dependencies` → `DependencyPage`；依赖创建、更新、归档、恢复 → `DependencyResponse`。
- `GET /api/v1/incidents` → `IncidentPage`；事件详情、创建、更新、归档、恢复 → `IncidentResponse`。
- `GET /api/v1/audit-logs` → `AuditLogPage`；`GET /api/v1/overview` → `OverviewResponse`。
- 动作预览、审批 → `ActionResponse`；诊断 → `DiagnosisResponse`。
- 204 注销接口不添加 body 模型。

- [ ] **Step 4: 重新生成 OpenAPI 与 TypeScript schema**

Run: `pnpm generate:api`

Expected: `services/ops-api/openapi.json` 与 `packages/api-client/src/schema.ts` 更新，列表响应不再是 `{[key: string]: unknown}`。

- [ ] **Step 5: 前端只重导出生成类型**

`api/types.ts` 保留 `NodeInfo`、`TopologyEdge` 这类纯 UI/概览内部类型；API 实体改为：

```typescript
import type { components } from '@kylin-aiops/api-client'

type Schemas = components['schemas']
export type HumanRole = Schemas['UserCreate']['role']
export type CurrentUser = Schemas['AuthUser']
export type Incident = Schemas['IncidentResponse']
export type UserAccount = Schemas['UserResponse']
export type ManagedNode = Schemas['NodeResponse']
export type Service = Schemas['ServiceResponse']
export type ServiceDependency = Schemas['DependencyResponse']
export type AuditLog = Schemas['AuditLogResponse']
```

删除未使用的 `UserCreateInput`、`NodeCreateInput` 和 `IncidentCreateInput`。

- [ ] **Step 6: 把请求 body 从 `object` 改为生成输入类型**

事件请求改为完整实现：

```typescript
createIncident: (body: Schemas['IncidentCreate']) => request<Incident>(
  '/api/v1/incidents',
  { method: 'POST', body: JSON.stringify(body) },
),
updateIncident: (id: string, version: number, body: Schemas['IncidentUpdate']) =>
  request<Incident>(
    `/api/v1/incidents/${id}`,
    { method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body) },
  ),
```

其余输入类型映射锁定为：`createUser → UserCreate`、`updateUser → UserUpdate`、`createNode → NodeCreate`、`updateNode → NodeUpdate`、`createService → ServiceCreate`、`updateService → ServiceUpdate`、`createDependency → DependencyCreate`、`updateDependency → DependencyUpdate`。这些方法都保留当前 URL、HTTP method 和 `If-Match` 行为，禁止保留 `body: object`。

- [ ] **Step 7: 运行合约与构建检查**

Run: `./.venv/Scripts/python.exe -m pytest tests/api/test_openapi_contract.py -q`

Run: `pnpm build:web`

Expected: PASS；TypeScript 不依赖手写重复响应结构。

- [ ] **Step 8: 提交**

```bash
git add services/ops-api/src/kylin_aiops_api/schemas.py services/ops-api/src/kylin_aiops_api/main.py services/ops-api/src/kylin_aiops_api/management.py services/ops-api/openapi.json packages/api-client/src/schema.ts apps/web/src/api/types.ts apps/web/src/api/client.ts tests/api/test_openapi_contract.py
git commit -m "refactor: 统一 OpenAPI 前后端类型契约"
```

---

### Task 8: 实现前端服务端分页、资源懒加载和标签规范化

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Modify: `apps/web/src/features/incidents/IncidentsPage.tsx`
- Modify: `apps/web/src/features/incidents/IncidentTable.tsx`
- Modify: `apps/web/src/features/management/UsersPage.tsx`
- Modify: `apps/web/src/features/management/ResourcesPage.tsx`
- Modify: `apps/web/src/features/management/AuditPage.tsx`
- Modify: corresponding `*.test.tsx` files

- [ ] **Step 1: 定义统一列表参数**

```typescript
export interface ListParams {
  page: number
  pageSize: number
  includeArchived?: boolean
  q?: string
}

function listQuery(params: ListParams): string {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  })
  if (params.includeArchived) query.set('include_archived', 'true')
  if (params.q) query.set('q', params.q)
  return query.toString()
}
```

所有列表 API 接受对象参数；禁止继续隐式请求第一页。

- [ ] **Step 2: 写入事件第二页交互测试**

模拟第一页 `total: 25`，点击 Ant Design 分页第二页后断言：

```typescript
expect(api.incidents).toHaveBeenLastCalledWith({ page: 2, pageSize: 20 })
```

- [ ] **Step 3: 将表格改为受控分页**

页面状态固定使用：

```typescript
const [page, setPage] = useState(1)
const [pageSize, setPageSize] = useState(20)
const query = useQuery({
  queryKey: ['incidents', page, pageSize],
  queryFn: () => api.incidents({ page, pageSize }),
})
```

表格 `pagination` 传入 `current`、`pageSize`、`total` 和 `onChange`；改变 `pageSize` 时把页码重置为 1。用户、审计、节点、服务和依赖表格采用相同规则。

- [ ] **Step 4: 只加载当前资源标签页**

`ResourcesPage` 增加 `activeKind`；三个主列表查询分别设置：

```typescript
enabled: activeKind === 'node'
```

服务编辑器仅在打开时请求节点候选，依赖编辑器仅在打开时请求服务候选；候选查询使用 `pageSize: 100` 和输入搜索 `q`，不在进入页面时并发加载三类数据。

- [ ] **Step 5: 统一节点标签转换**

```typescript
export function parseTags(value: unknown): string[] {
  return String(value ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
```

创建和编辑节点都执行 `{ ...values, tags: parseTags(values.tags) }`。增加测试，编辑 `教学楼, ARM` 时断言 API 收到 `['教学楼', 'ARM']`。

- [ ] **Step 6: 统一 mutation 错误处理**

归档、恢复按钮也必须使用 `useMutation` 或显式 `try/catch`；不得保留没有 `.catch()` 的 `api.*().then(refresh)`。409 显示版本冲突，其他 `ApiError` 显示后端 `message`。

- [ ] **Step 7: 运行前端测试**

Run: `pnpm test:web`

Run: `pnpm lint:web`

Run: `pnpm build:web`

Expected: 全部通过；翻页触发服务端请求，标签编辑不再发送字符串，资源页初始只发当前标签的一条列表请求。

- [ ] **Step 8: 提交**

```bash
git add apps/web/src/api/client.ts apps/web/src/features/incidents apps/web/src/features/management
git commit -m "fix: 接入服务端分页并规范化资源表单"
```

---

### Task 9: 删除伪实时链路、无效依赖和重复工作区文件

**Files:**
- Delete: `apps/web/src/app/EventStreamBridge.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/api/client.ts`
- Modify: `apps/web/src/features/overview/OverviewPage.tsx`
- Modify: `apps/web/src/features/incidents/IncidentsPage.tsx`
- Modify: `services/ops-api/src/kylin_aiops_api/main.py`
- Modify: `apps/web/package.json`
- Modify: `pnpm-lock.yaml`
- Delete: `apps/web/pnpm-lock.yaml`
- Delete: `packages/api-client/pnpm-lock.yaml`

- [ ] **Step 1: 删除只发送心跳的 SSE 路由和客户端**

删除 `main.py::event_stream()`、`streamEvents()`、`EventStreamBridge` import/render 和 `asyncio`/`StreamingResponse` 的无用 import。

- [ ] **Step 2: 保留单一刷新策略**

概览和事件页列表查询均使用：

```typescript
refetchInterval: 15_000,
```

其他管理页不自动轮询；成功 mutation 仅失效直接相关的 query key。

- [ ] **Step 3: 删除未使用客户端导出**

删除 `getAccessToken()`、`api.incident()`、`api.diagnose()` 和 `api.evaluation()`；保留后端详情/诊断接口，因为它们属于公共 API，不因当前页面未调用而删除。

- [ ] **Step 4: 删除未使用图表依赖并统一锁文件**

Run: `pnpm --filter @kylin-aiops/web remove echarts echarts-for-react`

然后删除两个子目录 `pnpm-lock.yaml`，只保留 workspace 根锁文件。不得手工编辑锁文件依赖节点。

- [ ] **Step 5: 验证请求和构建产物**

Run: `pnpm test:web`

Run: `pnpm lint:web`

Run: `pnpm build:web`

Expected: PASS；应用不再建立 SSE 连接；主入口 gzip 体积不得高于当前基线 245.06 kB。若 Vite 仍提示原始 chunk 超过 600 kB，只记录实际体积，不通过提高 `chunkSizeWarningLimit` 隐藏告警。

- [ ] **Step 6: 提交**

```bash
git add apps/web/src/app apps/web/src/api/client.ts apps/web/src/features/overview/OverviewPage.tsx apps/web/src/features/incidents/IncidentsPage.tsx services/ops-api/src/kylin_aiops_api/main.py apps/web/package.json pnpm-lock.yaml apps/web/pnpm-lock.yaml packages/api-client/pnpm-lock.yaml
git commit -m "chore: 删除重复刷新链路与未使用依赖"
```

---

### Task 10: 全量验证、性能验收与文档同步

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/test-report.md`
- Modify: `docs/api-management.md`
- Modify: `README.md`

- [ ] **Step 1: 更新架构文档**

明确记录：数据库模式下 PostgreSQL 是唯一业务状态源；`InMemoryStore` 仅用于测试/演示；遥测是按节点覆盖的最新快照；Redis 队列按节点隔离；前端通过 15 秒轮询刷新概览和事件。

- [ ] **Step 2: 更新 API 文档**

为列表接口补充 `page/page_size/q/include_archived` 示例和分页响应；删除 SSE 使用说明；保留动作 API 路径不变。

- [ ] **Step 3: 执行完整后端门禁**

Run: `./.venv/Scripts/python.exe -m pytest`

Expected: 所有测试通过，除依赖真实 MindIE/硬件的既有跳过项外无新增 skip。

Run: `./.venv/Scripts/ruff.exe check .`

Expected: `All checks passed!`

- [ ] **Step 4: 执行完整前端和合约门禁**

Run: `pnpm generate:api`

Run: `pnpm test:web`

Run: `pnpm lint:web`

Run: `pnpm build:web`

Expected: 全部退出码为 0。

- [ ] **Step 5: 验证生成文件无漂移**

Run: `git diff --exit-code services/ops-api/openapi.json packages/api-client/src/schema.ts`

Expected: 无输出；提交的 OpenAPI 与生成客户端一致。

- [ ] **Step 6: 执行定向性能验收**

- 20 条事件列表业务 SQL 不超过 4 条。
- 25 条用户数据可以访问第二页，页面无重复 ID。
- 150 条其他节点动作不会阻塞目标节点动作。
- 单次遥测只更新目标 `nodes` 行和目标 `telemetry_snapshots` 行。
- 资源页初始只请求当前标签页列表。
- 前端不存在 `/api/v1/events/stream` 网络请求。

- [ ] **Step 7: 检查注释语言与工作树**

Run: `rg -n '"""[A-Za-z]|// [A-Za-z]|/\*\* [A-Za-z]' services/ops-api/src apps/web/src`

Expected: 本次触及文件不新增英文模块说明、docstring 或代码注释；协议名和标识符除外。

Run: `git status --short`

Expected: 只包含本任务计划内的文档变更。

- [ ] **Step 8: 提交最终文档**

```bash
git add README.md docs/architecture.md docs/test-report.md docs/api-management.md
git commit -m "docs: 更新单一状态源与性能验收说明"
```

---

## 完成标准

- 数据库中新建或更新的事件可立即被概览、诊断、问答和动作接口读取。
- 生产数据库路径不存在全量内存镜像或 `persist_all()`。
- 所有列表由数据库分页，事件列表不存在逐事件查询。
- 动作队列不扫描其他节点消息，单条消息不会被两个并发消费者同时取走。
- 前端可以访问第二页数据，节点标签创建和编辑使用相同数据格式。
- OpenAPI 生成的主要响应都是具体 schema，前端不再维护同名手写实体类型。
- SSE、两个未使用图表依赖和两个重复子锁文件被删除。
- 后端测试、Ruff、前端测试、ESLint、TypeScript 构建和 OpenAPI 漂移检查全部通过。

## 默认假设

- 保留现有 HTTP 路径、角色权限、`If-Match` 乐观锁和软删除语义。
- 保留 Redis 动作队列当前“取走即消费”的至多一次语义；需要崩溃重投时再单独设计 consumer group 与回执协议。
- 不迁移或保留旧进程内遥测历史，因为当前实现只保存每节点最新值。
- 数据库迁移从当前唯一 initial revision 继续，不压缩或重写已经提交的迁移历史。
- 前端初始性能预算采用当前构建基线，不通过调整告警阈值制造表面改善。

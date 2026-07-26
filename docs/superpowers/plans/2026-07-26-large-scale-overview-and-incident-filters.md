# Large-Scale Overview and Incident Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 10,000 条压测数据场景下以聚合拓扑替代物理节点渲染，记录压测操作审计，并提供可分页的事件筛选。

**Architecture:** `SqlControlPlaneStore.overview()` 通过 SQL 聚合生成服务类型/状态摘要和服务依赖摘要；物理节点拓扑只保留给小数据量与内存演示。压测脚本在其原子事务内写入一条系统审计记录。事件筛选参数由 React URL 查询参数传递到 API，并在数据库查询中完成过滤、排序和分页。

**Tech Stack:** FastAPI、SQLAlchemy 2、PostgreSQL/SQLite、React、TypeScript、Ant Design、React Query、React Flow、pytest、Vitest。

---

## 文件结构

- `services/ops-api/src/kylin_aiops_api/schemas.py`：新增聚合拓扑 API 模型。
- `services/ops-api/src/kylin_aiops_api/sql_store.py`：以数据库聚合查询生成总览摘要，限制物理拓扑回传。
- `services/ops-api/src/kylin_aiops_api/store.py`：为内存演示模式生成同结构聚合摘要。
- `services/ops-api/src/kylin_aiops_api/load_data.py`：为压测写入与清理增加系统审计记录。
- `services/ops-api/src/kylin_aiops_api/management.py`：事件筛选与节点明细跳转所需的服务端查询参数。
- `apps/web/src/api/client.ts`：定义事件、节点筛选参数并序列化查询字符串。
- `apps/web/src/features/overview/ServiceTopology.tsx`：显示聚合拓扑并暴露聚合节点点击事件。
- `apps/web/src/features/overview/OverviewPage.tsx`：消费聚合拓扑并导航到已筛选的节点管理页。
- `apps/web/src/features/incidents/IncidentsPage.tsx`：筛选栏、URL 状态同步和分页重置。
- `apps/web/src/features/management/ResourcesPage.tsx`：读取聚合跳转参数并应用节点筛选。

### Task 1: 建立聚合总览 API

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/schemas.py:135-159`
- Modify: `services/ops-api/src/kylin_aiops_api/sql_store.py:56-143`
- Modify: `services/ops-api/src/kylin_aiops_api/store.py`
- Test: `tests/integration/test_sql_store.py`
- Test: `tests/api/test_api.py`

- [ ] **Step 1: 写出聚合响应的失败测试**

```python
def test_overview_groups_large_database_nodes_without_returning_physical_nodes(tmp_path):
    store = build_sql_store(tmp_path, nodes=240, services=("nginx", "java", "mysql"))

    overview = store.overview()

    assert overview["nodes"] == []
    assert {(item["service"], item["status"], item["count"]) for item in overview["topology_groups"]} == {
        ("nginx", "online", 80), ("java", "online", 80), ("mysql", "offline", 80)
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run: `\.venv\Scripts\python.exe -m pytest tests\integration\test_sql_store.py -q`

Expected: FAIL，响应中没有 `topology_groups`，且仍装载物理节点。

- [ ] **Step 3: 定义稳定的聚合响应模型**

在 `schemas.py` 添加：

```python
class TopologyGroupResponse(BaseModel):
    id: str
    service: str
    status: str
    count: int


class TopologyGroupEdgeResponse(BaseModel):
    source_service: str
    target_service: str
    count: int
    confidence: float
```

并在 `OverviewResponse` 增加：

```python
topology_groups: list[TopologyGroupResponse] = Field(default_factory=list)
topology_group_edges: list[TopologyGroupEdgeResponse] = Field(default_factory=list)
```

- [ ] **Step 4: 实现数据库聚合与物理数据上限**

在 `SqlControlPlaneStore.overview()` 先执行总节点数查询；当数量大于 `200` 时，使用 `NodeRow` 与 `ServiceRow` 的外连接和 `group_by(ServiceRow.service_type, NodeRow.status)` 构造 `topology_groups`，并返回空的 `nodes` 与 `topology`。依赖边使用两个 `aliased(ServiceRow)` 按源/目标服务类型分组，并返回 `count` 与 `func.avg(DependencyEdgeRow.confidence)`。

物理节点数不超过 `200` 时保留现有 `nodes`、`topology` 行为，同时从内存节点数据构建等价的摘要。内存 `ControlPlaneStore.overview()` 也返回同名的空列表或聚合列表，保证 API 结构一致。

- [ ] **Step 5: 运行聚合测试与 API 契约测试**

Run: `\.venv\Scripts\python.exe -m pytest tests\integration\test_sql_store.py tests\api\test_api.py -q`

Expected: PASS，超过 200 个节点时不返回物理节点，统计正确。

- [ ] **Step 6: 提交聚合 API**

```powershell
git add services/ops-api/src/kylin_aiops_api/schemas.py services/ops-api/src/kylin_aiops_api/sql_store.py services/ops-api/src/kylin_aiops_api/store.py tests/integration/test_sql_store.py tests/api/test_api.py
git commit -m "feat: aggregate large scale overview topology"
```

### Task 2: 记录压测脚本系统审计

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/load_data.py:1-100`
- Test: `tests/integration/test_load_data.py`

- [ ] **Step 1: 写出压测审计失败测试**

```python
def test_seed_and_purge_write_one_system_audit_entry(session):
    seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))
    seeded = session.scalars(select(AuditLogRow).where(AuditLogRow.action == "system.load_data_seeded")).all()

    assert len(seeded) == 1
    assert seeded[0].actor_id == "system"
    assert seeded[0].details == {"count": 2, "seed": 42, "batch_size": 2}

    purge_load_data(fresh_session())
    assert session.scalar(select(func.count()).select_from(AuditLogRow).where(AuditLogRow.action == "system.load_data_purged")) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `\.venv\Scripts\python.exe -m pytest tests\integration\test_load_data.py -q`

Expected: FAIL，尚未生成 `system.load_data_seeded` 或 `system.load_data_purged`。

- [ ] **Step 3: 在同一事务写入系统审计行**

在 `load_data.py` 导入 `AuditLogRow` 与 `uuid`，新增私有函数：

```python
def _record_load_data_audit(session: Session, action: str, details: dict[str, int]) -> None:
    session.add(AuditLogRow(
        id=str(uuid.uuid4()), actor_id="system", action=action,
        target="load-data", request_id=str(uuid.uuid4()), details=details,
        created_at=datetime.now(UTC),
    ))
```

在成功批量写入后、`session.commit()` 前调用 `system.load_data_seeded`；在成功删除后、提交前调用 `system.load_data_purged`。清理记录详情只含删除的四类计数；被外部引用保护拒绝或异常回滚时不得调用该函数。

- [ ] **Step 4: 运行压测审计测试**

Run: `\.venv\Scripts\python.exe -m pytest tests\integration\test_load_data.py -q`

Expected: PASS，幂等重复写入每次仅增加一条操作审计，清理也仅增加一条。

- [ ] **Step 5: 提交压测审计**

```powershell
git add services/ops-api/src/kylin_aiops_api/load_data.py tests/integration/test_load_data.py
git commit -m "feat: audit load data operations"
```

### Task 3: 扩展事件与节点服务端筛选

**Files:**
- Modify: `services/ops-api/src/kylin_aiops_api/management.py:352-388, 389-500, 730-820`
- Test: `tests/api/test_management.py`

- [ ] **Step 1: 写出组合事件筛选失败测试**

```python
def test_incident_list_filters_by_severity_keyword_and_start_time(management_client):
    response = management_client.get(
        "/api/v1/incidents?severity=critical&q=node-01&started_from=2026-07-01T00:00:00Z",
        headers=login(management_client, "admin", "correct-horse-battery-staple"),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["inc-critical-node-01"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `\.venv\Scripts\python.exe -m pytest tests\api\test_management.py -q`

Expected: FAIL，当前接口忽略 `severity`、`q` 和时间参数。

- [ ] **Step 3: 在数据库语句中执行筛选**

为 `incidents()` 增加 `severity`、`q`、`started_from`、`started_to` 查询参数。使用：

```python
if severity:
    statement = statement.where(IncidentRow.severity == severity)
if q:
    statement = statement.where(or_(IncidentRow.title.contains(q), IncidentRow.root_node_id.contains(q)))
if started_from:
    statement = statement.where(IncidentRow.started_at >= started_from)
if started_to:
    statement = statement.where(IncidentRow.started_at <= started_to)
```

保留 `page_scalars(... order_by(IncidentRow.started_at.desc()), page, page_size)`，使计数和分页针对筛选后的查询执行。

同时为节点列表增加 `status` 与 `service_type` 查询参数：使用 `ServiceRow` 外连接过滤服务类型，供聚合节点跳转使用；不带参数时保持当前节点列表结果。

- [ ] **Step 4: 运行事件与节点筛选测试**

Run: `\.venv\Scripts\python.exe -m pytest tests\api\test_management.py -q`

Expected: PASS，组合筛选、无匹配空页、分页总数和节点类型筛选均符合预期。

- [ ] **Step 5: 提交服务端筛选**

```powershell
git add services/ops-api/src/kylin_aiops_api/management.py tests/api/test_management.py
git commit -m "feat: filter incidents and managed nodes"
```

### Task 4: 用聚合拓扑替换大规模前端画布

**Files:**
- Modify: `apps/web/src/api/types.ts`
- Modify: `apps/web/src/features/overview/ServiceTopology.tsx`
- Modify: `apps/web/src/features/overview/OverviewPage.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/features/overview/ServiceTopology.test.tsx`
- Test: `apps/web/src/features/overview/OverviewPage.test.tsx`

- [ ] **Step 1: 写出聚合拓扑失败测试**

```tsx
test('聚合拓扑只渲染服务状态摘要并传递点击筛选条件', () => {
  const onSelectGroup = vi.fn()
  render(<ServiceTopology topologyGroups={[{ id: 'nginx:online', service: 'nginx', status: 'online', count: 6667 }]} topologyGroupEdges={[]} onSelectGroup={onSelectGroup} />)

  fireEvent.click(screen.getByRole('button', { name: /Nginx.*6667/ }))
  expect(onSelectGroup).toHaveBeenCalledWith({ service: 'nginx', status: 'online' })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm --filter @kylin-aiops/web test -- ServiceTopology.test.tsx`

Expected: FAIL，组件尚不接受 `topologyGroups`。

- [ ] **Step 3: 实现聚合节点与导航**

在 `ServiceTopology` 新增 `topologyGroups`、`topologyGroupEdges`、`onSelectGroup` 属性。存在聚合数据时，为每个组渲染一个可访问按钮式节点，显示服务名称、状态和数量，并只根据聚合边绘制 React Flow 边；没有聚合数据时保留物理节点逻辑。

在 `OverviewPage` 使用 `useNavigate()`，传入：

```typescript
onSelectGroup={({ service, status }) => navigate(
  `/management/resources?tab=nodes&service_type=${encodeURIComponent(service)}&status=${encodeURIComponent(status)}`,
)}
```

更新 CSS，使聚合卡片在窄屏时换行、长服务名不溢出，并让零摘要使用 `Empty` 状态。

- [ ] **Step 4: 运行总览前端测试**

Run: `pnpm --filter @kylin-aiops/web test -- ServiceTopology.test.tsx OverviewPage.test.tsx`

Expected: PASS，聚合数据不会创建物理节点卡片，点击传递正确筛选条件。

- [ ] **Step 5: 提交聚合前端**

```powershell
git add apps/web/src/api/types.ts apps/web/src/features/overview/ServiceTopology.tsx apps/web/src/features/overview/OverviewPage.tsx apps/web/src/styles.css apps/web/src/features/overview/ServiceTopology.test.tsx apps/web/src/features/overview/OverviewPage.test.tsx
git commit -m "feat: render aggregated service topology"
```

### Task 5: 实现事件中心筛选栏与 URL 同步

**Files:**
- Modify: `apps/web/src/api/client.ts:14-45, 130-140`
- Modify: `apps/web/src/features/incidents/IncidentsPage.tsx:1-110`
- Modify: `apps/web/src/features/management/ResourcesPage.tsx`
- Test: `apps/web/src/features/incidents/IncidentsPage.test.tsx`
- Test: `apps/web/src/features/management/ResourcesPage.test.tsx`

- [ ] **Step 1: 写出前端筛选失败测试**

```tsx
test('筛选严重级别后从第一页请求服务端事件列表', async () => {
  renderIncidentPage('/incidents?severity=critical&q=load-node')

  await waitFor(() => expect(api.incidents).toHaveBeenCalledWith({
    page: 1, pageSize: 20, severity: 'critical', q: 'load-node',
  }))
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm --filter @kylin-aiops/web test -- IncidentsPage.test.tsx`

Expected: FAIL，当前请求只包含 `page` 和 `pageSize`。

- [ ] **Step 3: 实现筛选参数和 URL 状态**

在 `client.ts` 定义：

```typescript
export interface IncidentListParams extends ListParams {
  status?: string
  severity?: string
  source?: string
  q?: string
  started_from?: string
  started_to?: string
}
```

`api.incidents()` 仅序列化存在的筛选字段。`IncidentsPage` 使用 `useSearchParams()` 读取并更新这些字段，表单提交或重置时写回 URL、将页码设为 `1`，并让 React Query 键包含整个筛选对象。筛选栏使用 `Select`、`Input.Search` 和 `DatePicker.RangePicker`，字段为状态、严重级别、来源、关键词和开始时间范围。

`ResourcesPage` 从 URL 读取 `service_type` 和 `status`，将它们传给 `api.nodes()`，并在节点页签显示当前筛选标签和重置按钮。

- [ ] **Step 4: 运行前端筛选测试**

Run: `pnpm --filter @kylin-aiops/web test -- IncidentsPage.test.tsx ResourcesPage.test.tsx`

Expected: PASS，筛选与重置请求参数正确，聚合跳转参数被节点页消费。

- [ ] **Step 5: 完整验证并提交**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
pnpm test:web
pnpm lint:web
pnpm build:web
```

Expected: 后端、前端测试、静态检查和构建均通过。

```powershell
git add apps/web/src/api/client.ts apps/web/src/features/incidents/IncidentsPage.tsx apps/web/src/features/management/ResourcesPage.tsx apps/web/src/features/incidents/IncidentsPage.test.tsx apps/web/src/features/management/ResourcesPage.test.tsx
git commit -m "feat: add incident center filters"
```

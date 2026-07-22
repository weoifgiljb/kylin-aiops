# 工程质量门禁补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为仓库添加可重复执行的 CI 门禁，消除已知前端测试噪声，并把大型第三方依赖从入口构建产物中拆出。

**Architecture:** GitHub Actions 将后端与前端验证拆成独立任务，均由锁定的运行时和仓库命令驱动。Vitest 的测试初始化只补齐 JSDOM 缺失能力并精确过滤两个已知噪声，Vite 通过供应商组分包保持现有路由懒加载不变。

**Tech Stack:** GitHub Actions、Python 3.11、pytest、Ruff、Node.js 22、pnpm、Vitest、JSDOM、Vite 7、React 19。

---

## 文件结构

- Create: `.github/workflows/quality-gates.yml` — 在 GitHub 托管环境运行后端与前端门禁。
- Modify: `apps/web/src/test/setup.ts` — 仅为 JSDOM 提供前端组件测试所需的兼容层，并过滤已知输出噪声。
- Modify: `apps/web/vite.config.ts` — 将 Ant Design 及其图标从入口依赖中拆成独立 vendor chunk。
- Modify: `docs/test-report.md` — 记录可复跑的门禁和仍需目标环境完成的验收项。

### Task 1: 为 JSDOM 测试环境消除已知噪声

**Files:**
- Modify: `apps/web/src/test/setup.ts`

- [ ] **Step 1: 运行现有前端测试并确认噪声基线**

Run: `pnpm test:web`

Expected: 命令退出码为 0，输出包含 `Could not parse CSS stylesheet` 和 `Not implemented: Window's getComputedStyle() method: with pseudo-elements`。

- [ ] **Step 2: 增加最小 JSDOM 兼容处理**

在 `apps/web/src/test/setup.ts` 的 `matchMedia` 定义后追加以下代码，并将现有英文注释改为表达相同设计意图的简体中文：

```ts
const nativeGetComputedStyle = window.getComputedStyle.bind(window)

Object.defineProperty(window, 'getComputedStyle', {
  writable: true,
  value: (element: Element, pseudoElement?: string | null) =>
    nativeGetComputedStyle(element, pseudoElement ? undefined : null),
})

const nativeConsoleError = console.error

console.error = (...args: unknown[]) => {
  const message = String(args[0] ?? '')
  if (
    message.includes('Could not parse CSS stylesheet') ||
    message.includes("Not implemented: Window's getComputedStyle() method: with pseudo-elements")
  ) {
    return
  }
  nativeConsoleError(...args)
}
```

设计约束：非伪元素调用必须保持调用原生 `getComputedStyle`；除两个精确匹配的 JSDOM 消息外，所有控制台错误仍必须打印。

- [ ] **Step 3: 运行前端测试验证输出干净**

Run: `pnpm test:web`

Expected: 12 个测试文件、20 个测试通过；输出不再包含 Step 1 的两类已知消息。

- [ ] **Step 4: 提交测试环境改动**

```bash
git add apps/web/src/test/setup.ts
git commit -m "test: silence known jsdom limitations"
```

### Task 2: 将 Ant Design 从入口依赖中拆出

**Files:**
- Modify: `apps/web/vite.config.ts`

- [ ] **Step 1: 执行构建并记录当前入口资产**

Run: `pnpm build:web`

Expected: 构建通过，输出包含一个大于 600 kB 的 `index-*.js` 入口 chunk 警告。

- [ ] **Step 2: 为 Ant Design 添加稳定的 vendor chunk**

在 `apps/web/vite.config.ts` 的 `manualChunks` 内保留现有 `react`、`react-flow` 与 `state` 映射，并追加：

```ts
          antd: ['antd', '@ant-design/icons'],
```

不要修改 `chunkSizeWarningLimit`，不要移除现有的路由懒加载或手工 chunk。

- [ ] **Step 3: 运行构建验证分包**

Run: `pnpm build:web`

Expected: 构建通过，资产列表包含 `antd-*.js`，入口 `index-*.js` 小于 600 kB；如果其他 chunk 仍超限，保留 Vite 原始警告。

- [ ] **Step 4: 提交构建配置改动**

```bash
git add apps/web/vite.config.ts
git commit -m "perf: split antd vendor chunk"
```

### Task 3: 添加 GitHub Actions 质量门禁

**Files:**
- Create: `.github/workflows/quality-gates.yml`

- [ ] **Step 1: 创建工作流定义**

创建 `.github/workflows/quality-gates.yml`，内容如下：

```yaml
name: Quality gates

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e '.[dev]'
      - run: python -m pytest
      - run: python -m ruff check .

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 10.24.0
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm generate:api
      - run: git diff --exit-code
      - run: pnpm test:web
      - run: pnpm lint:web
      - run: pnpm build:web
```

- [ ] **Step 2: 校验 YAML 与工作流命令**

Run: `pnpm install --frozen-lockfile; pnpm generate:api; git diff --exit-code; pnpm test:web; pnpm lint:web; pnpm build:web`

Expected: 所有命令成功，`git diff --exit-code` 不输出差异。GitHub Actions 文件不含仓库密钥、部署命令或发布权限。

- [ ] **Step 3: 提交工作流**

```bash
git add .github/workflows/quality-gates.yml
git commit -m "ci: add quality gate workflow"
```

### Task 4: 更新验证报告并执行完整门禁

**Files:**
- Modify: `docs/test-report.md`

- [ ] **Step 1: 在“2026-07-22 本地门禁结果”后新增质量门禁段落**

追加以下内容：

```markdown
## 持续集成质量门禁

`.github/workflows/quality-gates.yml` 会在推送和 Pull Request 时独立执行以下任务：

- 后端：Python 3.11、`python -m pytest` 与 `python -m ruff check .`。
- 前端：锁文件安装、`pnpm generate:api` 后的 `git diff --exit-code`、`pnpm test:web`、`pnpm lint:web` 与 `pnpm build:web`。

该工作流只验证仓库内可复现的代码质量，不替代目标麒麟环境、真实 PostgreSQL/Redis、Ascend/MindIE、120 次盲测或断网重装验收。
```

- [ ] **Step 2: 运行完整本地门禁**

Run: `python -m pytest; python -m ruff check .; pnpm generate:api; git diff --exit-code; pnpm test:web; pnpm lint:web; pnpm build:web; docker compose --env-file .env.example -f infra/compose/compose.yml config --quiet`

Expected: Python、前端、生成无漂移与 Compose 配置验证全部通过；不启动容器，不声明真实环境验收已完成。

- [ ] **Step 3: 检查工作树与提交文档**

Run: `git diff --check; git status --short`

Expected: `git diff --check` 无输出，工作树只包含本任务文档改动。

```bash
git add docs/test-report.md
git commit -m "docs: document quality gates"
```

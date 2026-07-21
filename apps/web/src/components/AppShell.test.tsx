import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { AppShell } from './AppShell'

vi.mock('../api/client', () => ({
  api: {
    systemStatus: vi.fn().mockResolvedValue({
      checked_at: '2026-07-19T16:40:00Z',
      components: {
        deterministic_diagnosis: {
          status: 'available', backend: 'rules_topology', detail: '规则与拓扑诊断模块已加载',
        },
      },
    }),
  },
}))

const admin = { id: 'admin-1', username: 'admin', display_name: '系统管理员', role: 'admin' as const }
const viewer = { id: 'viewer-1', username: 'viewer', display_name: '访客', role: 'viewer' as const }

function renderShell(user: typeof admin | typeof viewer) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}><MemoryRouter>
      <AppShell user={user} onLogout={() => undefined}><div>content</div></AppShell>
    </MemoryRouter></QueryClientProvider>,
  )
}

test('shows product and admin areas for an administrator', () => {
  renderShell(admin)

  for (const label of ['态势总览', '事件中心', '智能问答', '评测报告', '系统设置', '资源管理', '用户管理', '审计日志']) {
    expect(screen.getByText(label)).toBeInTheDocument()
  }
})

test('hides administrator menus from a viewer', () => {
  renderShell(viewer)

  expect(screen.queryByText('资源管理')).not.toBeInTheDocument()
  expect(screen.queryByText('用户管理')).not.toBeInTheDocument()
  expect(screen.queryByText('审计日志')).not.toBeInTheDocument()
})

test('shows the deterministic diagnosis status returned by the API', async () => {
  renderShell(admin)

  expect(await screen.findByText('规则诊断可用')).toBeInTheDocument()
})

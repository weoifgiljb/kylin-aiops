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

test('shows the five approved product areas', () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}><MemoryRouter>
      <AppShell><div>content</div></AppShell>
    </MemoryRouter></QueryClientProvider>,
  )

  for (const label of ['态势总览', '事件中心', '智能问答', '评测报告', '系统设置']) {
    expect(screen.getByText(label)).toBeInTheDocument()
  }
})

test('shows the deterministic diagnosis status returned by the API', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}><MemoryRouter>
      <AppShell><div>content</div></AppShell>
    </MemoryRouter></QueryClientProvider>,
  )

  expect(await screen.findByText('规则诊断可用')).toBeInTheDocument()
})

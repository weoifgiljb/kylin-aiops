import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { App } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import OverviewPage from './OverviewPage'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('react-router-dom', async (importOriginal) => ({
  ...await importOriginal<typeof import('react-router-dom')>(),
  useNavigate: () => navigate,
}))

vi.mock('../../api/client', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      online_nodes: 6667,
      total_nodes: 10000,
      active_incidents: 8,
      today_alerts: 4,
      pending_actions: 1,
      nodes: [],
      topology: [],
      topology_groups: [
        { id: 'nginx:online', service: 'nginx', status: 'online', count: 6667 },
      ],
      topology_group_edges: [],
    }),
    incidents: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  },
}))

test('点击聚合服务状态摘要后跳转至已筛选的节点资源页', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App><OverviewPage /></App>
      </MemoryRouter>
    </QueryClientProvider>,
  )

  fireEvent.click(await screen.findByLabelText('Nginx 在线 6,667 个节点', { selector: 'button' }))

  expect(navigate).toHaveBeenCalledWith('/management/resources?tab=nodes&service_type=nginx&status=online')
})

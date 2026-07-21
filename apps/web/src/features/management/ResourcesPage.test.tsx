import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import ResourcesPage from './ResourcesPage'

vi.mock('../../api/client', () => ({
  api: {
    nodes: vi.fn().mockResolvedValue({
      items: [{ id: 'node-01', display_name: '教学楼节点', description: '', tags: [], enabled: true, status: 'offline', version: 1 }],
      total: 1, page: 1, page_size: 20,
    }),
    services: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
    dependencies: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  },
}))

test('shows managed nodes and all resource categories', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><ResourcesPage /></QueryClientProvider>)

  expect(await screen.findByText('教学楼节点')).toBeInTheDocument()
  expect(screen.getByText('节点')).toBeInTheDocument()
  expect(screen.getByText('服务')).toBeInTheDocument()
  expect(screen.getByText('依赖关系')).toBeInTheDocument()
})

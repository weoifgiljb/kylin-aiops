import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { api } from '../../api/client'
import ResourcesPage from './ResourcesPage'

vi.mock('../../api/client', () => ({
  api: {
    nodes: vi.fn().mockResolvedValue({
      items: [{ id: 'node-01', display_name: '教学楼节点', description: '', tags: ['旧标签'], enabled: true, status: 'offline', version: 1 }],
      total: 1, page: 1, page_size: 20,
    }),
    services: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
    dependencies: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
    updateNode: vi.fn().mockResolvedValue({}),
  },
}))

test('shows managed nodes and all resource categories', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><ResourcesPage /></QueryClientProvider>)

  expect(await screen.findByText('教学楼节点')).toBeInTheDocument()
  expect(screen.getByText('节点')).toBeInTheDocument()
  expect(screen.getByText('服务')).toBeInTheDocument()
  expect(screen.getByText('依赖关系')).toBeInTheDocument()
  expect(api.services).not.toHaveBeenCalled()
  expect(api.dependencies).not.toHaveBeenCalled()
})

test('normalizes tags when editing a node', async () => {
  const user = userEvent.setup()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><ResourcesPage /></QueryClientProvider>)

  await screen.findByText('教学楼节点')
  await user.click(screen.getByRole('button', { name: /编\s*辑/ }))
  const tags = screen.getByLabelText('标签（逗号分隔）')
  await user.clear(tags)
  await user.type(tags, '教学楼, ARM')
  await user.click(screen.getByRole('button', { name: 'OK' }))

  await waitFor(() => expect(api.updateNode).toHaveBeenCalledWith(
    'node-01',
    1,
    expect.objectContaining({ tags: ['教学楼', 'ARM'] }),
  ))
})

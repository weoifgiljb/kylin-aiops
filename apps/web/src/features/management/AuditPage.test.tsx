import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import AuditPage from './AuditPage'

vi.mock('../../api/client', () => ({
  api: {
    auditLogs: vi.fn().mockResolvedValue({
      items: [{ id: 'audit-1', actor_id: 'admin-1', action: 'node.created', target: 'node:node-01', request_id: 'request-1', details: {}, created_at: '2026-07-21T08:00:00Z' }],
      total: 1, page: 1, page_size: 20,
    }),
  },
}))

test('renders immutable audit entries', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><AuditPage /></QueryClientProvider>)

  expect(await screen.findByText('node.created')).toBeInTheDocument()
  expect(screen.getByText('node:node-01')).toBeInTheDocument()
  expect(screen.getByText('只读')).toBeInTheDocument()
})

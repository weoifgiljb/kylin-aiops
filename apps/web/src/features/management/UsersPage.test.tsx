import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import UsersPage from './UsersPage'

vi.mock('../../api/client', () => ({
  api: {
    users: vi.fn().mockResolvedValue({
      items: [{ id: 'user-1', username: 'operator', display_name: '值班人员', role: 'operator', is_active: true, version: 1, created_at: '', updated_at: '' }],
      total: 1, page: 1, page_size: 20,
    }),
  },
}))

test('shows user role and account state', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><UsersPage /></QueryClientProvider>)

  expect(await screen.findByText('值班人员')).toBeInTheDocument()
  expect(screen.getAllByText('operator')).toHaveLength(2)
  expect(screen.getByText('启用')).toBeInTheDocument()
})

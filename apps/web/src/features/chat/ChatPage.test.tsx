import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { api } from '../../api/client'
import { useUiStore } from '../../store/ui'
import ChatPage from './ChatPage'

vi.mock('../../api/client', () => ({
  api: {
    chat: vi.fn().mockResolvedValue({ answer: 'live answer', evidence_refs: [] }),
  },
}))

test('sends the currently selected live incident instead of a demo incident', async () => {
  useUiStore.setState({ selectedIncidentId: 'inc-live-alert' })
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><ChatPage /></QueryClientProvider>)

  fireEvent.change(screen.getByPlaceholderText(/例如/), { target: { value: '发生了什么？' } })
  fireEvent.click(screen.getByRole('button', { name: /发\s*送/ }))

  await waitFor(() => expect(api.chat).toHaveBeenCalledWith('default', '发生了什么？', 'inc-live-alert'))
})

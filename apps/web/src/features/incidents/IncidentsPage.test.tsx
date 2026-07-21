import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { App } from 'antd'
import { vi } from 'vitest'

import IncidentsPage from './IncidentsPage'

vi.mock('../../api/client', () => ({
  api: {
    incidents: vi.fn().mockResolvedValue({
      items: [{
        id: 'inc-manual-1', title: '人工巡检异常', fault_type: 'manual_check', severity: 'medium',
        status: 'open', source: 'manual', started_at: '2026-07-21T08:00:00Z', root_node: '',
        assignee_user_id: null, handling_notes: '', version: 1, archived_at: null,
        propagation_path: [], evidence: [], diagnosis: { summary: '等待诊断', root_cause: '', severity: 'medium', propagation_path: [], evidence_refs: [], recommended_steps: [], action_candidates: [], confidence: 0, source: 'deterministic_fallback' },
      }],
      total: 1, page: 1, page_size: 20,
    }),
  },
}))

test('shows incident source and manual incident controls', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><App><IncidentsPage /></App></QueryClientProvider>)

  expect(await screen.findByText('人工巡检异常')).toBeInTheDocument()
  expect(screen.getByText('人工')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /新增人工事件/ })).toBeInTheDocument()
})

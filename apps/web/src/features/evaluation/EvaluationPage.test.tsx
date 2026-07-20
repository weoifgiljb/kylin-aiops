import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { api } from '../../api/client'
import EvaluationPage from './EvaluationPage'

const { evaluationsMock } = vi.hoisted(() => ({
  evaluationsMock: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  api: {
    evaluations: evaluationsMock,
  },
}))

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EvaluationPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  evaluationsMock.mockReset()
})

test('shows an explicit empty state instead of drawing thresholds as measured progress', async () => {
  evaluationsMock.mockResolvedValue({ items: [], total: 0 })

  renderPage()

  expect(await screen.findByText('暂无真实评测结果')).toBeInTheDocument()
  expect(screen.queryAllByRole('progressbar')).toHaveLength(0)
  expect(api.evaluations).toHaveBeenCalledOnce()
})

test('renders measured values only from a generated evaluation report', async () => {
  evaluationsMock.mockResolvedValue({
    items: [{
      id: 'blind-run-20260720',
      status: 'passed',
      trial_count: 120,
      thresholds: { detection_f1: 0.85 },
      metrics: { detection_f1: 0.9 },
    }],
    total: 1,
  })

  renderPage()

  expect(await screen.findByText('实测 90.0% / 门槛 85.0%')).toBeInTheDocument()
  expect(screen.getByText('blind-run-20260720')).toBeInTheDocument()
})

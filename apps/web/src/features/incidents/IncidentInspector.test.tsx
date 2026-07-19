import { render, screen } from '@testing-library/react'

import { IncidentInspector } from './IncidentInspector'
import type { Incident } from '../../api/types'

const incident: Incident = {
  id: 'inc-1',
  title: '数据库连接池耗尽',
  severity: 'high',
  status: 'open',
  started_at: '2026-07-19T14:32:08+08:00',
  root_node: 'db-01',
  propagation_path: ['db-01', 'app-01', 'web-01'],
  evidence: [
    { id: 'ev-1', kind: 'metric', node_id: 'db-01', summary: 'connections=498/500', observed_at: '2026-07-19T14:32:08+08:00' },
  ],
  diagnosis: {
    summary: '测试连接占满。',
    root_cause: 'db-01',
    severity: 'high',
    propagation_path: ['db-01', 'app-01', 'web-01'],
    evidence_refs: ['ev-1'],
    recommended_steps: ['终止测试连接', '复查健康状态'],
    action_candidates: ['terminate_fault_db_sessions'],
    confidence: 0.86,
    source: 'deterministic_fallback',
  },
}

test('renders root cause, propagation path and real evidence ids', () => {
  render(<IncidentInspector incident={incident} onApprove={() => undefined} />)

  expect(screen.getByText('db-01')).toBeInTheDocument()
  expect(screen.getByText('db-01 → app-01 → web-01')).toBeInTheDocument()
  expect(screen.getByText('ev-1')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '审批并执行' })).toBeInTheDocument()
})

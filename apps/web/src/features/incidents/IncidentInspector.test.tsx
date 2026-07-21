import { render, screen } from '@testing-library/react'

import type { Incident } from '../../api/types'
import { IncidentInspector } from './IncidentInspector'

const incident: Incident = {
  id: 'inc-1',
  title: '数据库连接池耗尽',
  fault_type: 'db_connection',
  severity: 'high',
  status: 'open',
  source: 'alert',
  started_at: '2026-07-19T14:32:08+08:00',
  root_node: 'db-01',
  handling_notes: '',
  version: 1,
  archived_at: null,
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

test('展示根因、传播路径和真实证据编号', () => {
  render(<IncidentInspector incident={incident} onApprove={() => undefined} />)

  expect(screen.getByText('db-01')).toBeInTheDocument()
  expect(screen.getByText('db-01 → app-01 → web-01')).toBeInTheDocument()
  expect(screen.getByText('ev-1')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /审\s*批并执行/ })).toBeInTheDocument()
})

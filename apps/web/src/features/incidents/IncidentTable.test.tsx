import { render, screen } from '@testing-library/react'

import { IncidentTable } from './IncidentTable'

const incident = {
  id: 'inc-load-1', title: '压测事件', fault_type: 'load_test', severity: 'medium',
  status: 'open', source: 'load-data', started_at: '2026-07-21T08:00:00Z', root_node: '',
  assignee_user_id: null, handling_notes: '', version: 1, archived_at: null,
  propagation_path: [], evidence: [], diagnosis: { summary: '', root_cause: '', severity: 'medium', propagation_path: [], evidence_refs: [], recommended_steps: [], action_candidates: [], confidence: 0, source: 'deterministic_fallback' },
}

test('shows load-data and unknown sources without mislabeling them as alerts', () => {
  render(<IncidentTable incidents={[incident, { ...incident, id: 'inc-unknown-1', source: 'external-sync' }]} onSelect={() => undefined} />)

  expect(screen.getByText('批量加载数据')).toBeInTheDocument()
  expect(screen.getByText('未知来源（external-sync）')).toBeInTheDocument()
  expect(screen.queryByText('告警')).not.toBeInTheDocument()
})

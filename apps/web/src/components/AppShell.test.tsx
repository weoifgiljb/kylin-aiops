import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AppShell } from './AppShell'

test('shows the five approved product areas', () => {
  render(
    <MemoryRouter>
      <AppShell><div>content</div></AppShell>
    </MemoryRouter>,
  )

  for (const label of ['态势总览', '事件中心', '智能问答', '评测报告', '系统设置']) {
    expect(screen.getByText(label)).toBeInTheDocument()
  }
})

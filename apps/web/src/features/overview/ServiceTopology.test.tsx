import { render, screen } from '@testing-library/react'

import { ServiceTopology } from './ServiceTopology'

test('拓扑节点和图例使用一致的根因、传播中、正常配色', () => {
  const { container } = render(
    <ServiceTopology
      nodes={[
        { id: 'web-01', hostname: 'web-01', status: 'online', service: 'nginx' },
        { id: 'app-01', hostname: 'app-01', status: 'online', service: 'java' },
        { id: 'db-01', hostname: 'db-01', status: 'online', service: 'mysql' },
      ]}
      topology={[
        { source: 'web-01', target: 'app-01', confidence: 1 },
        { source: 'app-01', target: 'db-01', confidence: 1 },
      ]}
      rootNode="db-01"
      propagationPath={['db-01', 'app-01']}
    />,
  )

  expect(screen.getByText('Nginx')).toBeInTheDocument()
  expect(screen.getByText('Java 服务')).toBeInTheDocument()
  expect(screen.getByText('MySQL')).toBeInTheDocument()
  expect(container.querySelector('.flow-node-root')).toHaveStyle({ borderColor: '#ef4444' })
  expect(container.querySelector('.flow-node-propagating')).toHaveStyle({ borderColor: '#f59e0b' })
  expect(container.querySelector('.flow-node-normal')).toHaveStyle({ borderColor: '#22c55e' })
  expect(screen.getByLabelText('根因颜色')).toHaveStyle({ backgroundColor: '#ef4444' })
  expect(screen.getByLabelText('传播中颜色')).toHaveStyle({ backgroundColor: '#f59e0b' })
  expect(screen.getByLabelText('正常颜色')).toHaveStyle({ backgroundColor: '#22c55e' })
})

test('renders live metrics reported by an enrolled agent', () => {
  render(
    <ServiceTopology
      nodes={[
        {
          id: 'local-dev-01',
          hostname: 'developer-pc',
          status: 'online',
          last_seen_at: '2026-07-19T16:40:00Z',
          metrics: { cpu_percent: 12.5, memory_percent: 34.5 },
        },
      ]}
      topology={[]}
    />,
  )

  expect(screen.getByText('local-dev-01')).toBeInTheDocument()
  expect(screen.getByText('CPU 12.5% · 内存 34.5%')).toBeInTheDocument()
})

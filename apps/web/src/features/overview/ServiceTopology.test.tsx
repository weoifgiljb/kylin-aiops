import { render, screen } from '@testing-library/react'

import { ServiceTopology } from './ServiceTopology'

test('renders the fixed three-node lab dependency chain', () => {
  render(
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
    />,
  )

  expect(screen.getByText('Nginx')).toBeInTheDocument()
  expect(screen.getByText('Java 服务')).toBeInTheDocument()
  expect(screen.getByText('MySQL')).toBeInTheDocument()
})

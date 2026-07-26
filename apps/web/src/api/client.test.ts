import { afterEach, expect, test, vi } from 'vitest'

import { api } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

test('serializes incident and node filter parameters', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
  })
  vi.stubGlobal('fetch', fetchMock)

  await api.incidents({
    page: 1,
    pageSize: 20,
    includeArchived: true,
    status: 'open',
    severity: 'critical',
    source: 'load-data',
    q: 'load-node',
    started_from: '2026-07-01T00:00:00Z',
    started_to: '2026-07-02T00:00:00Z',
  })
  await api.nodes({ page: 1, pageSize: 20, status: 'online', service_type: 'nginx' })

  expect(fetchMock.mock.calls[0][0]).toContain(
    '/api/v1/incidents?page=1&page_size=20&include_archived=true&q=load-node&status=open&severity=critical&source=load-data&started_from=2026-07-01T00%3A00%3A00Z&started_to=2026-07-02T00%3A00%3A00Z',
  )
  expect(fetchMock.mock.calls[1][0]).toContain(
    '/api/v1/resources/nodes?page=1&page_size=20&status=online&service_type=nginx',
  )
})

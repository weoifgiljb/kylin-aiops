import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { api } from '../../api/client'
import SettingsPage from './SettingsPage'

vi.mock('../../api/client', () => ({
  api: {
    systemStatus: vi.fn().mockResolvedValue({
      checked_at: '2026-07-19T16:40:00Z',
      components: {
        deterministic_diagnosis: {
          status: 'available', backend: 'rules_topology', detail: '规则与拓扑诊断模块已加载',
        },
        mindspore: {
          status: 'degraded', backend: 'DeterministicFallback', detail: '模型服务在线，但正在使用确定性降级推理',
        },
        generative_ai: {
          status: 'available', backend: 'Ollama', model: 'llama3.1:latest', detail: '配置模型已加载',
        },
      },
    }),
  },
  getToken: () => 'dev-operator-token',
  setToken: vi.fn(),
}))

test('renders model status returned by the center API', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><SettingsPage /></QueryClientProvider>)

  fireEvent.click(screen.getByText('模型状态'))

  expect(await screen.findByText('Ollama / llama3.1:latest')).toBeInTheDocument()
  expect(screen.getByText('DeterministicFallback')).toBeInTheDocument()
  expect(api.systemStatus).toHaveBeenCalledOnce()
})

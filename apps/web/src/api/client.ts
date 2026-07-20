import type {
  ApiProblemBody,
  EvaluationRun,
  EvaluationRunList,
  Incident,
  Overview,
  SystemStatus,
} from './types'

const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  constructor(public readonly problem: ApiProblemBody, public readonly status: number) {
    super(problem.message)
  }
}

export function getToken(): string {
  return localStorage.getItem('kylin_aiops_token') ?? 'dev-operator-token'
}

export function setToken(token: string): void {
  localStorage.setItem('kylin_aiops_token', token)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Authentication and the uniform API error envelope are centralized here so
  // feature components cannot accidentally bypass either contract.
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const problem = await response.json() as ApiProblemBody
    throw new ApiError(problem, response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  overview: () => request<Overview>('/api/v1/overview'),
  systemStatus: () => request<SystemStatus>('/api/v1/system/status'),
  incidents: () => request<{ items: Incident[]; total: number }>('/api/v1/incidents'),
  incident: (id: string) => request<Incident>(`/api/v1/incidents/${id}`),
  diagnose: (id: string) => request<Incident['diagnosis']>(`/api/v1/incidents/${id}/diagnose`, { method: 'POST' }),
  chat: (sessionId: string, message: string, incidentId?: string) =>
    request<{ answer: string; source: string; evidence_refs: string[] }>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify({ message, incident_id: incidentId }) },
    ),
  previewAction: (incidentId: string, body: object) =>
    request<{ id: string; status: string }>(`/api/v1/incidents/${incidentId}/actions/preview`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  approveAction: (actionId: string) =>
    request<{ id: string; status: string }>(`/api/v1/action-requests/${actionId}/approve`, { method: 'POST' }),
  evaluations: () => request<EvaluationRunList>('/api/v1/evaluations/runs'),
  evaluation: (id: string) => request<EvaluationRun>(`/api/v1/evaluations/runs/${id}`),
}

export async function streamEvents(signal: AbortSignal, onEvent: () => void): Promise<void> {
  const response = await fetch(`${apiBase}/api/v1/events/stream`, {
    headers: { Authorization: `Bearer ${getToken()}` },
    signal,
  })
  if (!response.ok || !response.body) throw new Error('事件流连接失败')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (!signal.aborted) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const messages = buffer.split('\n\n')
    buffer = messages.pop() ?? ''
    messages.forEach(() => onEvent())
  }
}

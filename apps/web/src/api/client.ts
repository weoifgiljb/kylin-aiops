import type { components } from '@kylin-aiops/api-client'

import type {
  ApiProblemBody,
  CurrentUser,
  EvaluationRun,
  EvaluationRunList,
  Incident,
  ManagedNode,
  Overview,
  Service,
  ServiceDependency,
  SystemStatus,
  UserAccount,
} from './types'

type Schemas = components['schemas']

export interface ListParams {
  page: number
  pageSize: number
  includeArchived?: boolean
  q?: string
}

export interface AuditLogParams extends ListParams {
  actor_id?: string
  action?: string
  target?: string
  created_from?: string
  created_to?: string
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
let accessToken: string | null = null
let refreshPromise: Promise<string> | null = null

export class ApiError extends Error {
  constructor(public readonly problem: ApiProblemBody, public readonly status: number) {
    super(problem.message)
  }
}

export function getAccessToken(): string | null {
  return accessToken
}

export function clearAccessToken(): void {
  accessToken = null
  localStorage.removeItem('kylin_aiops_token')
}

async function parseError(response: Response): Promise<ApiProblemBody> {
  try {
    return await response.json() as ApiProblemBody
  } catch {
    return {
      code: 'HTTP_ERROR',
      message: `接口请求失败（${response.status}）`,
      request_id: '',
      details: {},
    }
  }
}

async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${apiBase}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    }).then(async (response) => {
      if (!response.ok) throw new ApiError(await parseError(response), response.status)
      const body = await response.json() as { access_token: string }
      accessToken = body.access_token
      return body.access_token
    }).finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

async function request<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  })
  if (response.status === 401 && retry && !path.startsWith('/api/v1/auth/')) {
    await refreshAccessToken()
    return request<T>(path, init, false)
  }
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function versionHeader(version: number): HeadersInit {
  return { 'If-Match': `"${version}"` }
}

function listQuery(params: ListParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  })
  if (params.includeArchived) query.set('include_archived', 'true')
  if (params.q) query.set('q', params.q)
  return query
}

export const api = {
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password })
    const response = await fetch(`${apiBase}/api/v1/auth/token`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!response.ok) throw new ApiError(await parseError(response), response.status)
    const result = await response.json() as { access_token: string }
    accessToken = result.access_token
  },
  refresh: refreshAccessToken,
  logout: async () => {
    try {
      await request<void>('/api/v1/auth/logout', { method: 'POST' }, false)
    } finally {
      clearAccessToken()
    }
  },
  me: () => request<CurrentUser>('/api/v1/auth/me', undefined, false),
  overview: () => request<Overview>('/api/v1/overview'),
  systemStatus: () => request<SystemStatus>('/api/v1/system/status'),
  incidents: (params: ListParams) => request<Schemas['IncidentPage']>(
    `/api/v1/incidents?${listQuery(params)}`,
  ),
  incident: (id: string) => request<Incident>(`/api/v1/incidents/${id}`),
  createIncident: (body: Schemas['IncidentCreate']) => request<Incident>('/api/v1/incidents', {
    method: 'POST', body: JSON.stringify(body),
  }),
  updateIncident: (id: string, version: number, body: Schemas['IncidentUpdate']) =>
    request<Incident>(`/api/v1/incidents/${id}`, {
      method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body),
    }),
  archiveIncident: (id: string, version: number) => request<Incident>(`/api/v1/incidents/${id}`, {
    method: 'DELETE', headers: versionHeader(version),
  }),
  restoreIncident: (id: string, version: number) => request<Incident>(`/api/v1/incidents/${id}/restore`, {
    method: 'POST', headers: versionHeader(version),
  }),
  diagnose: (id: string) => request<Incident['diagnosis']>(`/api/v1/incidents/${id}/diagnose`, { method: 'POST' }),
  chat: (sessionId: string, message: string, incidentId?: string) =>
    request<{ answer: string; source: string; evidence_refs: string[] }>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify({ message, incident_id: incidentId }) },
    ),
  previewAction: (incidentId: string, body: Schemas['ActionPreview']) =>
    request<{ id: string; status: string }>(`/api/v1/incidents/${incidentId}/actions/preview`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  approveAction: (actionId: string) =>
    request<{ id: string; status: string }>(`/api/v1/action-requests/${actionId}/approve`, { method: 'POST' }),
  evaluations: () => request<EvaluationRunList>('/api/v1/evaluations/runs'),
  evaluation: (id: string) => request<EvaluationRun>(`/api/v1/evaluations/runs/${id}`),
  users: (params: ListParams) => request<Schemas['UserPage']>(
    `/api/v1/admin/users?${listQuery(params)}`,
  ),
  createUser: (body: Schemas['UserCreate']) => request<UserAccount>('/api/v1/admin/users', {
    method: 'POST', body: JSON.stringify(body),
  }),
  updateUser: (id: string, version: number, body: Schemas['UserUpdate']) => request<UserAccount>(`/api/v1/admin/users/${id}`, {
    method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body),
  }),
  archiveUser: (id: string, version: number) => request<UserAccount>(`/api/v1/admin/users/${id}`, {
    method: 'DELETE', headers: versionHeader(version),
  }),
  restoreUser: (id: string, version: number) => request<UserAccount>(`/api/v1/admin/users/${id}/restore`, {
    method: 'POST', headers: versionHeader(version),
  }),
  resetUserPassword: (id: string, version: number, password: string) => request<UserAccount>(`/api/v1/admin/users/${id}/reset-password`, {
    method: 'POST', headers: versionHeader(version), body: JSON.stringify({ password }),
  }),
  nodes: (params: ListParams) => request<Schemas['NodePage']>(
    `/api/v1/resources/nodes?${listQuery(params)}`,
  ),
  createNode: (body: Schemas['NodeCreate']) => request<ManagedNode>('/api/v1/resources/nodes', {
    method: 'POST', body: JSON.stringify(body),
  }),
  updateNode: (id: string, version: number, body: Schemas['NodeUpdate']) => request<ManagedNode>(`/api/v1/resources/nodes/${id}`, {
    method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body),
  }),
  archiveNode: (id: string, version: number) => request<ManagedNode>(`/api/v1/resources/nodes/${id}`, {
    method: 'DELETE', headers: versionHeader(version),
  }),
  restoreNode: (id: string, version: number) => request<ManagedNode>(`/api/v1/resources/nodes/${id}/restore`, {
    method: 'POST', headers: versionHeader(version),
  }),
  services: (params: ListParams) => request<Schemas['ServicePage']>(
    `/api/v1/resources/services?${listQuery(params)}`,
  ),
  createService: (body: Schemas['ServiceCreate']) => request<Service>('/api/v1/resources/services', {
    method: 'POST', body: JSON.stringify(body),
  }),
  updateService: (id: string, version: number, body: Schemas['ServiceUpdate']) => request<Service>(`/api/v1/resources/services/${id}`, {
    method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body),
  }),
  archiveService: (id: string, version: number) => request<Service>(`/api/v1/resources/services/${id}`, {
    method: 'DELETE', headers: versionHeader(version),
  }),
  restoreService: (id: string, version: number) => request<Service>(`/api/v1/resources/services/${id}/restore`, {
    method: 'POST', headers: versionHeader(version),
  }),
  dependencies: (params: ListParams) => request<Schemas['DependencyPage']>(
    `/api/v1/resources/dependencies?${listQuery(params)}`,
  ),
  createDependency: (body: Schemas['DependencyCreate']) => request<ServiceDependency>('/api/v1/resources/dependencies', {
    method: 'POST', body: JSON.stringify(body),
  }),
  updateDependency: (id: number, version: number, body: Schemas['DependencyUpdate']) => request<ServiceDependency>(`/api/v1/resources/dependencies/${id}`, {
    method: 'PATCH', headers: versionHeader(version), body: JSON.stringify(body),
  }),
  archiveDependency: (id: number, version: number) => request<ServiceDependency>(`/api/v1/resources/dependencies/${id}`, {
    method: 'DELETE', headers: versionHeader(version),
  }),
  restoreDependency: (id: number, version: number) => request<ServiceDependency>(`/api/v1/resources/dependencies/${id}/restore`, {
    method: 'POST', headers: versionHeader(version),
  }),
  auditLogs: (params: AuditLogParams) => {
    const query = listQuery(params)
    for (const key of ['actor_id', 'action', 'target', 'created_from', 'created_to'] as const) {
      if (params[key]) query.set(key, params[key])
    }
    return request<Schemas['AuditLogPage']>(`/api/v1/audit-logs?${query}`)
  },
}

export async function streamEvents(signal: AbortSignal, onEvent: () => void): Promise<void> {
  const response = await fetch(`${apiBase}/api/v1/events/stream`, {
    credentials: 'include',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
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

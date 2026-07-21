import type { components } from '@kylin-aiops/api-client'

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export interface NodeInfo {
  id: string
  hostname: string
  status: 'online' | 'offline'
  service?: string
  architecture?: string
  kylin_version?: string
  last_seen_at?: string
  metrics?: Record<string, number>
}

export interface TopologyEdge {
  source: string
  target: string
  confidence: number
}

export interface Evidence {
  id: string
  kind: 'metric' | 'log' | 'trace' | 'stack'
  node_id: string
  summary: string
  observed_at: string
}

export interface Diagnosis {
  summary: string
  root_cause: string
  severity: Severity
  propagation_path: string[]
  evidence_refs: string[]
  recommended_steps: string[]
  action_candidates: string[]
  confidence: number
  source: 'mindie' | 'deterministic_fallback' | 'pending' | 'rule_baseline'
}

export interface Incident {
  id: string
  title: string
  fault_type: string
  severity: Severity
  status: string
  source: 'manual' | 'alert'
  started_at: string
  ended_at?: string | null
  root_node: string
  assignee_user_id?: string | null
  handling_notes: string
  version: number
  archived_at?: string | null
  propagation_path: string[]
  evidence: Evidence[]
  diagnosis: Diagnosis
}

export interface Overview {
  online_nodes: number
  total_nodes: number
  active_incidents: number
  today_alerts: number
  pending_actions: number
  nodes: NodeInfo[]
  topology: TopologyEdge[]
}

export type RuntimeState = 'available' | 'degraded' | 'unconfigured' | 'unreachable'

/** 后端单次观测状态；可选字段用于标识当前实际使用的实现。 */
export interface ComponentRuntimeStatus {
  status: RuntimeState
  detail: string
  backend?: string
  model?: string
}

/** ops-api 通过有界下游探测汇总的时间点状态。 */
export interface SystemStatus {
  checked_at: string
  components: {
    deterministic_diagnosis: ComponentRuntimeStatus
    mindspore: ComponentRuntimeStatus
    generative_ai: ComponentRuntimeStatus
  }
}

export interface EvaluationRun {
  id: string
  status: string
  trial_count: number
  thresholds: Record<string, number>
  metrics: Record<string, number>
  generated_at?: string
  seed?: number
  code_revision?: string
  model_sha256?: string | null
}

/** ops-api 发现的生成报告，按生成时间倒序排列。 */
export interface EvaluationRunList {
  items: EvaluationRun[]
  total: number
}

export interface ApiProblemBody {
  code: string
  message: string
  request_id: string
  details: unknown
}

export type HumanRole = components['schemas']['UserCreate']['role']
export type UserCreateInput = components['schemas']['UserCreate']
export type NodeCreateInput = components['schemas']['NodeCreate']
export type IncidentCreateInput = components['schemas']['IncidentCreate']

export interface CurrentUser {
  id: string
  username: string
  display_name: string
  role: HumanRole
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ManagedNode {
  id: string
  display_name: string
  description: string
  tags: string[]
  enabled: boolean
  hostname?: string | null
  architecture?: string | null
  kylin_version?: string | null
  status: string
  last_seen_at?: string | null
  version: number
  archived_at?: string | null
}

export interface Service {
  id: string
  node_id: string
  name: string
  service_type: string
  description: string
  enabled: boolean
  status: string
  version: number
  archived_at?: string | null
}

export interface ServiceDependency {
  id: number
  source_service_id: string
  target_service_id: string
  source: 'manual' | 'discovered'
  confidence: number
  version: number
  archived_at?: string | null
}

export interface UserAccount extends CurrentUser {
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  archived_at?: string | null
}

export interface AuditLog {
  id: string
  actor_id: string
  action: string
  target: string
  request_id: string
  details: Record<string, unknown>
  created_at: string
}

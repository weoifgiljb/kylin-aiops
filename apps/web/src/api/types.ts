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
  source: 'mindie' | 'deterministic_fallback'
}

export interface Incident {
  id: string
  title: string
  severity: Severity
  status: string
  started_at: string
  root_node: string
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

/** One observed backend state. Optional fields identify the implementation in use. */
export interface ComponentRuntimeStatus {
  status: RuntimeState
  detail: string
  backend?: string
  model?: string
}

/** Point-in-time status assembled by ops-api from bounded downstream probes. */
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

/** Generated reports discovered by ops-api, ordered newest first. */
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

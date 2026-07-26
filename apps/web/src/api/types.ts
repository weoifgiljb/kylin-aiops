import type { components } from '@kylin-aiops/api-client'

type Schemas = components['schemas']

export type Severity = Schemas['IncidentCreate']['severity']
export type HumanRole = Schemas['UserCreate']['role']
export type CurrentUser = Schemas['AuthUser']
export type Incident = Schemas['IncidentResponse']
export type Evidence = Schemas['EvidenceResponse']
export type Diagnosis = Schemas['DiagnosisResponse']
export type Overview = Schemas['OverviewResponse']
export type NodeInfo = Schemas['OverviewNodeResponse']
export type TopologyEdge = Schemas['TopologyEdgeResponse']
export type TopologyGroup = Schemas['TopologyGroupResponse']
export type TopologyGroupEdge = Schemas['TopologyGroupEdgeResponse']
export type UserAccount = Schemas['UserResponse']
export type ManagedNode = Schemas['NodeResponse']
export type Service = Schemas['ServiceResponse']
export type ServiceDependency = Schemas['DependencyResponse']
export type AuditLog = Schemas['AuditLogResponse']
export type SystemStatus = Schemas['SystemStatus']

export type RuntimeState = 'available' | 'degraded' | 'unconfigured' | 'unreachable'
export type ComponentRuntimeStatus = Schemas['ComponentStatus']

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

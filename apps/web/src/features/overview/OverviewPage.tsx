import { useMutation, useQueries } from '@tanstack/react-query'
import { App, Card, Col, Row, Skeleton, Statistic } from 'antd'
import { useMemo } from 'react'

import { api } from '../../api/client'
import type { Incident } from '../../api/types'
import { useUiStore } from '../../store/ui'
import { IncidentInspector } from '../incidents/IncidentInspector'
import { IncidentTable } from '../incidents/IncidentTable'
import { ServiceTopology } from './ServiceTopology'
import { actionParameters } from './actionParameters'

export default function OverviewPage() {
  const { message } = App.useApp()
  const selectedIncidentId = useUiStore((state) => state.selectedIncidentId)
  const setSelectedIncidentId = useUiStore((state) => state.setSelectedIncidentId)
  const [overviewQuery, incidentsQuery] = useQueries({ queries: [
    { queryKey: ['overview'], queryFn: api.overview, refetchInterval: 15_000 },
    { queryKey: ['incidents'], queryFn: api.incidents, refetchInterval: 15_000 },
  ] })
  const incidents = useMemo(() => incidentsQuery.data?.items ?? [], [incidentsQuery.data?.items])
  const selected = useMemo(() => incidents.find((item) => item.id === selectedIncidentId) ?? incidents[0], [incidents, selectedIncidentId])
  const approve = useMutation({
    mutationFn: async (incident: Incident) => {
      const actionName = incident.diagnosis.action_candidates[0]
      if (!actionName) throw new Error('当前诊断没有可执行的白名单动作')
      const preview = await api.previewAction(incident.id, { node_id: incident.root_node, action_name: actionName, parameters: actionParameters(actionName) })
      return api.approveAction(preview.id)
    },
    onSuccess: () => void message.success('动作已审批，等待目标 Agent 执行'),
    onError: (error) => void message.error(error instanceof Error ? error.message : '审批失败'),
  })

  if (overviewQuery.isLoading || incidentsQuery.isLoading) return <Skeleton active />
  if (overviewQuery.error || incidentsQuery.error || !overviewQuery.data) return <Card>中心服务不可用，请检查 API 与认证配置。</Card>
  const overview = overviewQuery.data

  return <div className="dashboard-grid">
    <main>
      <Row gutter={[16, 16]} className="summary-row">
        <Col xs={12} xl={6}><Card><Statistic title="在线节点" value={overview.online_nodes} suffix={`/ ${overview.total_nodes}`} /></Card></Col>
        <Col xs={12} xl={6}><Card><Statistic title="活跃事件" value={overview.active_incidents} styles={{ content: { color: '#d97706' } }} /></Card></Col>
        <Col xs={12} xl={6}><Card><Statistic title="今日告警" value={overview.today_alerts} styles={{ content: { color: '#dc2626' } }} /></Card></Col>
        <Col xs={12} xl={6}><Card><Statistic title="待审批动作" value={overview.pending_actions} styles={{ content: { color: '#2563eb' } }} /></Card></Col>
      </Row>
      <ServiceTopology nodes={overview.nodes} topology={overview.topology} rootNode={selected?.root_node} />
      <section className="incident-table-panel"><div className="section-heading"><div><span>实时事件</span><h2>事件列表</h2></div></div><IncidentTable incidents={incidents} selectedId={selected?.id} onSelect={(item) => setSelectedIncidentId(item.id)} /></section>
    </main>
    {selected ? <IncidentInspector incident={selected} onApprove={() => approve.mutate(selected)} /> : <aside className="incident-inspector">暂无事件</aside>}
  </div>
}

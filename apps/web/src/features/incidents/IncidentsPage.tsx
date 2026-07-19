import { useMutation, useQuery } from '@tanstack/react-query'
import { App, Card, Empty } from 'antd'
import { useState } from 'react'

import { api } from '../../api/client'
import type { Incident } from '../../api/types'
import { IncidentInspector } from './IncidentInspector'
import { IncidentTable } from './IncidentTable'
import { actionParameters } from '../overview/actionParameters'

export default function IncidentsPage() {
  const { message } = App.useApp()
  const { data } = useQuery({ queryKey: ['incidents'], queryFn: api.incidents })
  const [selected, setSelected] = useState<Incident | null>(null)
  const incidents = data?.items ?? []
  const approve = useMutation({
    mutationFn: async (incident: Incident) => {
      const actionName = incident.diagnosis.action_candidates[0]
      if (!actionName) throw new Error('当前诊断没有可执行的白名单动作')
      const preview = await api.previewAction(incident.id, {
        node_id: incident.root_node,
        action_name: actionName,
        parameters: actionParameters(actionName),
      })
      return api.approveAction(preview.id)
    },
    onSuccess: () => void message.success('动作已审批，等待目标 Agent 执行'),
    onError: (error) => void message.error(error instanceof Error ? error.message : '审批失败'),
  })
  return <div className="dashboard-grid"><Card title="事件中心"><IncidentTable incidents={incidents} selectedId={selected?.id} onSelect={setSelected} /></Card>{selected ? <IncidentInspector incident={selected} onApprove={() => approve.mutate(selected)} /> : <aside className="incident-inspector"><Empty description="选择一个事件查看证据" /></aside>}</div>
}

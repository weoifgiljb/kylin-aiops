import { Button, Divider, Tag, Typography } from 'antd'

import type { Incident } from '../../api/types'

export function IncidentInspector({ incident, onApprove }: { incident: Incident; onApprove: () => void }) {
  const evidenceById = new Map(incident.evidence.map((item) => [item.id, item]))
  return (
    <aside className="incident-inspector" aria-label="事件详情">
      <div className="inspector-title"><div><span>事件详情</span><h2>{incident.title}</h2></div><Tag color="red">{incident.severity}</Tag></div>
      <Divider />
      <section><Typography.Text type="secondary">根因结论</Typography.Text><h3>{incident.diagnosis.root_cause || '等待诊断'}</h3><p>{incident.diagnosis.summary}</p></section>
      <section><Typography.Text type="secondary">传播路径</Typography.Text><p className="path-text">{incident.diagnosis.propagation_path.join(' → ') || '暂无传播路径'}</p></section>
      <section><Typography.Text type="secondary">关键证据</Typography.Text>
        <div className="evidence-list">{incident.diagnosis.evidence_refs.map((id) => {
          const evidence = evidenceById.get(id)
          return <div className="evidence-row" key={id}><code>{id}</code><span>{evidence?.summary ?? '证据暂不可用'}</span></div>
        })}</div>
      </section>
      <section><Typography.Text type="secondary">修复建议</Typography.Text><ol>{incident.diagnosis.recommended_steps.map((step) => <li key={step}>{step}</li>)}</ol></section>
      <div className="inspector-actions"><Button type="primary" size="large" disabled={!incident.diagnosis.action_candidates.length} onClick={onApprove}>审批并执行</Button><Button size="large">仅保存方案</Button></div>
    </aside>
  )
}

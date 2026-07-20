import { useMutation } from '@tanstack/react-query'
import { Button, Card, Empty, Input, Typography } from 'antd'
import { useState } from 'react'

import { api } from '../../api/client'
import { useUiStore } from '../../store/ui'

interface Entry { role: 'user' | 'assistant'; text: string; evidence?: string[] }

export default function ChatPage() {
  const [input, setInput] = useState('')
  const [entries, setEntries] = useState<Entry[]>([])
  const selectedIncidentId = useUiStore((state) => state.selectedIncidentId)
  const mutation = useMutation({ mutationFn: (message: string) => api.chat('default', message, selectedIncidentId ?? undefined), onSuccess: (result) => setEntries((current) => [...current, { role: 'assistant', text: result.answer, evidence: result.evidence_refs }]) })
  const submit = () => { const value = input.trim(); if (!value) return; setEntries((current) => [...current, { role: 'user', text: value }]); setInput(''); mutation.mutate(value) }
  return <Card className="page-card" title="智能问答" extra={<Typography.Text type="secondary">回答必须引用真实 Evidence ID</Typography.Text>}><div className="chat-list">{entries.length === 0 ? <Empty description="可询问当前事件的根因、证据和处置步骤" /> : entries.map((entry, index) => <div key={`${entry.role}-${index}`} className={`chat-entry ${entry.role}`}><div><strong>{entry.role === 'user' ? '运维人员' : '麒麟智维'}</strong><p>{entry.text}</p>{entry.evidence?.map((id) => <code key={id}>{id}</code>)}</div></div>)}</div><div className="chat-compose"><Input.TextArea value={input} onChange={(event) => setInput(event.target.value)} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="例如：当前事件的根因证据是什么？" onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); submit() } }} /><Button type="primary" loading={mutation.isPending} onClick={submit}>发送</Button></div></Card>
}

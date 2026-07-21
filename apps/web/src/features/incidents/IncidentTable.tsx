import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import type { Incident } from '../../api/types'

const severityColors: Record<string, string> = { critical: 'magenta', high: 'red', medium: 'orange', low: 'green' }

export function IncidentTable({ incidents, selectedId, onSelect }: { incidents: Incident[]; selectedId?: string | null; onSelect: (incident: Incident) => void }) {
  const columns: ColumnsType<Incident> = [
    { title: '严重等级', dataIndex: 'severity', width: 110, render: (value: string) => <Tag color={severityColors[value]}>{value}</Tag> },
    { title: '来源', dataIndex: 'source', width: 80, render: (value: string) => <Tag color={value === 'manual' ? 'blue' : 'gold'}>{value === 'manual' ? '人工' : '告警'}</Tag> },
    { title: '事件', dataIndex: 'title' },
    { title: '根因节点', dataIndex: 'root_node', width: 120 },
    { title: '开始时间', dataIndex: 'started_at', width: 190, render: (value: string) => new Date(value).toLocaleString('zh-CN') },
    { title: '状态', dataIndex: 'status', width: 110 },
  ]
  return <Table rowKey="id" size="middle" pagination={{ pageSize: 20 }} columns={columns} dataSource={incidents} onRow={(record) => ({ onClick: () => onSelect(record), className: record.id === selectedId ? 'selected-row' : '' })} />
}

import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import type { Incident } from '../../api/types'
import { incidentSourceMeta } from './incidentSource'

const severityColors: Record<string, string> = { critical: 'magenta', high: 'red', medium: 'orange', low: 'green' }

interface Props {
  incidents: Incident[]
  selectedId?: string | null
  onSelect: (incident: Incident) => void
  page?: number
  pageSize?: number
  total?: number
  onPageChange?: (page: number, pageSize: number) => void
}

export function IncidentTable({
  incidents,
  selectedId,
  onSelect,
  page = 1,
  pageSize = 20,
  total = incidents.length,
  onPageChange,
}: Props) {
  const columns: ColumnsType<Incident> = [
    { title: '严重等级', dataIndex: 'severity', width: 110, render: (value: string) => <Tag color={severityColors[value]}>{value}</Tag> },
    { title: '来源', dataIndex: 'source', width: 120, render: (value: string) => {
      const source = incidentSourceMeta(value)
      return <Tag color={source.color}>{source.label}</Tag>
    } },
    { title: '事件', dataIndex: 'title' },
    { title: '根因节点', dataIndex: 'root_node', width: 120 },
    { title: '开始时间', dataIndex: 'started_at', width: 190, render: (value: string) => new Date(value).toLocaleString('zh-CN') },
    { title: '状态', dataIndex: 'status', width: 110 },
  ]
  return <Table rowKey="id" size="middle" pagination={onPageChange ? {
    current: page,
    pageSize,
    total,
    onChange: onPageChange,
  } : false} columns={columns} dataSource={incidents} onRow={(record) => ({ onClick: () => onSelect(record), className: record.id === selectedId ? 'selected-row' : '' })} />
}

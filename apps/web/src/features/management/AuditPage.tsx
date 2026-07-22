import { useQuery } from '@tanstack/react-query'
import { Button, Card, Form, Input, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'

import { api } from '../../api/client'

export default function AuditPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const logs = useQuery({
    queryKey: ['audit-logs', filters, page, pageSize],
    queryFn: () => api.auditLogs({ ...filters, page, pageSize }),
  })
  const columns = [
    { title: '时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString() },
    { title: '操作者', dataIndex: 'actor_id' },
    { title: '动作', dataIndex: 'action' },
    { title: '目标', dataIndex: 'target' },
    { title: '请求 ID', dataIndex: 'request_id' },
  ]
  return <Card className="page-card" title="审计日志" extra={<Tag>只读</Tag>}>
    <Typography.Paragraph type="secondary">记录登录安全事件及所有管理写操作，内容不可编辑或删除。</Typography.Paragraph>
    <Form
      layout="inline"
      onFinish={(values) => {
        setFilters(Object.fromEntries(Object.entries(values).filter(([, value]) => value)) as Record<string, string>)
        setPage(1)
      }}
      style={{ marginBottom: 16 }}
    >
      <Form.Item name="actor_id"><Input allowClear placeholder="操作者 ID" /></Form.Item>
      <Form.Item name="action"><Input allowClear placeholder="动作，例如 node.updated" /></Form.Item>
      <Form.Item name="target"><Input allowClear placeholder="目标" /></Form.Item>
      <Form.Item name="created_from"><Input allowClear type="datetime-local" aria-label="开始时间" /></Form.Item>
      <Form.Item name="created_to"><Input allowClear type="datetime-local" aria-label="结束时间" /></Form.Item>
      <Form.Item><Space><Button type="primary" htmlType="submit">筛选</Button><Button htmlType="reset" onClick={() => {
        setFilters({})
        setPage(1)
      }}>重置</Button></Space></Form.Item>
    </Form>
    <Table rowKey="id" loading={logs.isLoading} dataSource={logs.data?.items ?? []} columns={columns} pagination={{
      current: page,
      pageSize,
      total: logs.data?.total ?? 0,
      onChange: (nextPage, nextPageSize) => {
        setPage(nextPageSize === pageSize ? nextPage : 1)
        setPageSize(nextPageSize)
      },
    }} />
  </Card>
}

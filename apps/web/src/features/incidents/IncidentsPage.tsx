import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, DatePicker, Empty, Form, Input, Modal, Select, Space, Tag } from 'antd'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ApiError, api } from '../../api/client'
import type { Incident } from '../../api/types'
import { actionParameters } from '../overview/actionParameters'
import { IncidentInspector } from './IncidentInspector'
import { IncidentTable } from './IncidentTable'

export default function IncidentsPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const pageSize = Math.max(1, Number(searchParams.get('page_size')) || 20)
  const filters = useMemo(() => ({
    status: searchParams.get('status') || undefined,
    severity: searchParams.get('severity') || undefined,
    source: searchParams.get('source') || undefined,
    q: searchParams.get('q') || undefined,
    started_from: searchParams.get('started_from') || undefined,
    started_to: searchParams.get('started_to') || undefined,
  }), [searchParams])
  const { data } = useQuery({
    queryKey: ['incidents', page, pageSize, filters],
    queryFn: () => api.incidents({ page, pageSize, ...filters }),
    refetchInterval: 15_000,
  })
  const [selected, setSelected] = useState<Incident | null>(null)
  const [editing, setEditing] = useState<Incident | 'new' | null>(null)
  const [form] = Form.useForm()
  const incidents = data?.items ?? []
  const visibleSelected = selected && incidents.some((incident) => incident.id === selected.id) ? selected : null
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['incidents'] })

  function updateSearch(nextValues: Record<string, string | undefined>, resetPage = true) {
    setSelected(null)
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(nextValues)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (resetPage) next.set('page', '1')
    setSearchParams(next)
  }

  function resetFilters() {
    updateSearch({ status: undefined, severity: undefined, source: undefined, q: undefined, started_from: undefined, started_to: undefined })
  }
  const showError = (error: unknown) => void message.error(
    error instanceof ApiError && error.status === 409
      ? '数据已被其他人更新，请刷新列表后重试'
      : error instanceof Error ? error.message : '操作失败',
  )

  const save = useMutation({
    mutationFn: (values: Record<string, unknown>) => editing === 'new'
      ? api.createIncident(values as Parameters<typeof api.createIncident>[0])
      : api.updateIncident(
          editing!.id,
          editing!.version,
          values as Parameters<typeof api.updateIncident>[2],
        ),
    onSuccess: (incident) => {
      setEditing(null)
      setSelected(incident)
      form.resetFields()
      refresh()
      void message.success('事件已保存')
    },
    onError: showError,
  })
  const approve = useMutation({
    mutationFn: async (incident: Incident) => {
      const actionName = incident.diagnosis.action_candidates[0]
      if (!actionName) throw new Error('当前诊断没有可执行的白名单动作')
      if (!incident.root_node) throw new Error('当前事件没有可执行动作的目标节点')
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
  const toggleArchive = useMutation({
    mutationFn: (record: Incident) => record.archived_at
      ? api.restoreIncident(record.id, record.version)
      : api.archiveIncident(record.id, record.version),
    onSuccess: (incident) => {
      setSelected(incident)
      refresh()
    },
    onError: showError,
  })

  function openEditor(record: Incident | 'new') {
    setEditing(record)
    if (record === 'new') form.resetFields()
    else form.setFieldsValue(record)
  }

  return <div className="dashboard-grid">
    <Card title="事件中心" extra={<Button type="primary" onClick={() => openEditor('new')}>新增人工事件</Button>}>
      <Space wrap className="incident-filter-bar">
        <Select aria-label="状态" value={filters.status} allowClear placeholder="处理状态" style={{ width: 128 }} onChange={(value) => updateSearch({ status: value })} options={[
          { value: 'open', label: '待处理' }, { value: 'acknowledged', label: '已确认' },
          { value: 'resolving', label: '处理中' }, { value: 'resolved', label: '已解决' },
        ]} />
        <Select aria-label="严重等级" value={filters.severity} allowClear placeholder="严重等级" style={{ width: 128 }} onChange={(value) => updateSearch({ severity: value })} options={['low', 'medium', 'high', 'critical'].map((value) => ({ value, label: value }))} />
        <Select aria-label="来源" value={filters.source} allowClear placeholder="来源" style={{ width: 128 }} onChange={(value) => updateSearch({ source: value })} options={[
          { value: 'alert', label: '告警' }, { value: 'manual', label: '人工' },
        ]} />
        <Input.Search key={filters.q} aria-label="关键字" defaultValue={filters.q} allowClear placeholder="搜索事件或根因节点" style={{ width: 220 }} onSearch={(value) => updateSearch({ q: value.trim() || undefined })} />
        <DatePicker.RangePicker aria-label="开始时间范围" showTime onChange={(values) => updateSearch({
          started_from: values?.[0]?.toISOString(),
          started_to: values?.[1]?.toISOString(),
        })} />
        <Button onClick={resetFilters}>重置</Button>
      </Space>
      <IncidentTable
        incidents={incidents}
        selectedId={visibleSelected?.id}
        onSelect={setSelected}
        page={page}
        pageSize={pageSize}
        total={data?.total ?? 0}
        onPageChange={(nextPage, nextPageSize) => updateSearch({
          page: String(nextPageSize === pageSize ? nextPage : 1),
          page_size: String(nextPageSize),
        }, false)}
      />
    </Card>
    {visibleSelected ? <div>
      <Space className="incident-management-actions">
        <Tag color={visibleSelected.source === 'manual' ? 'blue' : 'gold'}>{visibleSelected.source === 'manual' ? '人工事件' : '自动告警'}</Tag>
        <Button onClick={() => openEditor(visibleSelected)}>编辑处置</Button>
        <Button disabled={!visibleSelected.archived_at && visibleSelected.status !== 'resolved'} danger={!visibleSelected.archived_at} onClick={() => toggleArchive.mutate(visibleSelected)}>{visibleSelected.archived_at ? '恢复' : '归档'}</Button>
      </Space>
      <IncidentInspector incident={visibleSelected} onApprove={() => approve.mutate(visibleSelected)} />
    </div> : <aside className="incident-inspector"><Empty description="选择一个事件查看证据" /></aside>}
    <Modal open={Boolean(editing)} title={editing === 'new' ? '新增人工事件' : '编辑事件'} confirmLoading={save.isPending} onCancel={() => setEditing(null)} onOk={() => void form.validateFields().then((values) => save.mutate(values))}>
      <Form form={form} layout="vertical">
        {editing === 'new' || (editing && editing.source === 'manual') ? <>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="故障类型" name="fault_type" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="根节点" name="root_node_id"><Input /></Form.Item>
        </> : null}
        <Form.Item label="严重级别" name="severity" rules={[{ required: true }]}><Select options={['low', 'medium', 'high', 'critical'].map((value) => ({ value, label: value }))} /></Form.Item>
        {editing !== 'new' ? <Form.Item label="处理状态" name="status"><Select options={['open', 'acknowledged', 'resolving', 'resolved'].map((value) => ({ value, label: value }))} /></Form.Item> : null}
        <Form.Item label="负责人用户 ID" name="assignee_user_id"><Input /></Form.Item>
        <Form.Item label="处置备注" name="handling_notes"><Input.TextArea rows={4} /></Form.Item>
      </Form>
    </Modal>
  </div>
}

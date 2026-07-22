import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Empty, Form, Input, Modal, Select, Space, Tag } from 'antd'
import { useState } from 'react'

import { ApiError, api } from '../../api/client'
import type { Incident } from '../../api/types'
import { actionParameters } from '../overview/actionParameters'
import { IncidentInspector } from './IncidentInspector'
import { IncidentTable } from './IncidentTable'

export default function IncidentsPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const { data } = useQuery({
    queryKey: ['incidents', page, pageSize],
    queryFn: () => api.incidents({ page, pageSize }),
    refetchInterval: 15_000,
  })
  const [selected, setSelected] = useState<Incident | null>(null)
  const [editing, setEditing] = useState<Incident | 'new' | null>(null)
  const [form] = Form.useForm()
  const incidents = data?.items ?? []
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['incidents'] })
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
      <IncidentTable
        incidents={incidents}
        selectedId={selected?.id}
        onSelect={setSelected}
        page={page}
        pageSize={pageSize}
        total={data?.total ?? 0}
        onPageChange={(nextPage, nextPageSize) => {
          setPage(nextPageSize === pageSize ? nextPage : 1)
          setPageSize(nextPageSize)
        }}
      />
    </Card>
    {selected ? <div>
      <Space className="incident-management-actions">
        <Tag color={selected.source === 'manual' ? 'blue' : 'gold'}>{selected.source === 'manual' ? '人工事件' : '自动告警'}</Tag>
        <Button onClick={() => openEditor(selected)}>编辑处置</Button>
        <Button disabled={!selected.archived_at && selected.status !== 'resolved'} danger={!selected.archived_at} onClick={() => toggleArchive.mutate(selected)}>{selected.archived_at ? '恢复' : '归档'}</Button>
      </Space>
      <IncidentInspector incident={selected} onApprove={() => approve.mutate(selected)} />
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

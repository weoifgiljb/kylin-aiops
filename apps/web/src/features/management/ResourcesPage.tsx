import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Checkbox, Form, Input, message, Modal, Select, Space, Switch, Table, Tabs, Tag } from 'antd'
import { useState } from 'react'

import { api } from '../../api/client'
import type { ManagedNode, Service, ServiceDependency } from '../../api/types'

type ResourceKind = 'node' | 'service' | 'dependency'

export default function ResourcesPage() {
  const queryClient = useQueryClient()
  const [includeArchived, setIncludeArchived] = useState(false)
  const [editor, setEditor] = useState<{ kind: ResourceKind; record?: ManagedNode | Service | ServiceDependency } | null>(null)
  const [form] = Form.useForm()
  const nodes = useQuery({ queryKey: ['managed-nodes', includeArchived], queryFn: () => api.nodes(includeArchived) })
  const services = useQuery({ queryKey: ['managed-services', includeArchived], queryFn: () => api.services(includeArchived) })
  const dependencies = useQuery({ queryKey: ['managed-dependencies', includeArchived], queryFn: () => api.dependencies(includeArchived) })

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['managed-nodes'] })
    void queryClient.invalidateQueries({ queryKey: ['managed-services'] })
    void queryClient.invalidateQueries({ queryKey: ['managed-dependencies'] })
  }

  const save = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (!editor) return
      if (editor.kind === 'node') {
        if (editor.record) {
          const node = editor.record as ManagedNode
          return api.updateNode(
            node.id,
            node.version,
            values as Parameters<typeof api.updateNode>[2],
          )
        }
        return api.createNode({
          ...values,
          tags: String(values.tags ?? '').split(',').filter(Boolean),
        } as Parameters<typeof api.createNode>[0])
      }
      if (editor.kind === 'service') {
        if (editor.record) {
          const service = editor.record as Service
          return api.updateService(
            service.id,
            service.version,
            values as Parameters<typeof api.updateService>[2],
          )
        }
        return api.createService(values as Parameters<typeof api.createService>[0])
      }
      if (editor.record && 'source' in editor.record) {
        return api.updateDependency(
          editor.record.id,
          editor.record.version,
          values as Parameters<typeof api.updateDependency>[2],
        )
      }
      return api.createDependency(values as Parameters<typeof api.createDependency>[0])
    },
    onSuccess: () => {
      setEditor(null)
      form.resetFields()
      refresh()
    },
    onError: () => void message.error('保存失败；如果数据已被他人更新，请保留输入并刷新版本'),
  })

  function openEditor(kind: ResourceKind, record?: ManagedNode | Service | ServiceDependency) {
    setEditor({ kind, record })
    if (record) {
      form.setFieldsValue({ ...record, tags: 'tags' in record ? record.tags.join(',') : undefined })
    } else {
      form.resetFields()
      form.setFieldsValue({ enabled: true })
    }
  }

  const nodeColumns = [
    { title: '标识', dataIndex: 'id' },
    { title: '名称', dataIndex: 'display_name' },
    { title: '观测状态', dataIndex: 'status', render: (value: string) => <Tag>{value}</Tag> },
    { title: '标签', dataIndex: 'tags', render: (values: string[]) => values.map((value) => <Tag key={value}>{value}</Tag>) },
    { title: '操作', render: (_: unknown, row: ManagedNode) => <Space>
      <Button size="small" onClick={() => openEditor('node', row)}>编辑</Button>
      {row.archived_at
        ? <Button size="small" onClick={() => void api.restoreNode(row.id, row.version).then(refresh)}>恢复</Button>
        : <Button size="small" danger onClick={() => void api.archiveNode(row.id, row.version).then(refresh)}>归档</Button>}
    </Space> },
  ]
  const serviceColumns = [
    { title: '标识', dataIndex: 'id' },
    { title: '名称', dataIndex: 'name' },
    { title: '所属节点', dataIndex: 'node_id' },
    { title: '类型', dataIndex: 'service_type' },
    { title: '操作', render: (_: unknown, row: Service) => <Space>
      <Button size="small" onClick={() => openEditor('service', row)}>编辑</Button>
      {row.archived_at
        ? <Button size="small" onClick={() => void api.restoreService(row.id, row.version).then(refresh)}>恢复</Button>
        : <Button size="small" danger onClick={() => void api.archiveService(row.id, row.version).then(refresh)}>归档</Button>}
    </Space> },
  ]
  const dependencyColumns = [
    { title: '源服务', dataIndex: 'source_service_id' },
    { title: '目标服务', dataIndex: 'target_service_id' },
    { title: '来源', dataIndex: 'source' },
    { title: '置信度', dataIndex: 'confidence' },
    { title: '操作', render: (_: unknown, row: ServiceDependency) => row.source === 'manual' ? <Space>
      <Button size="small" onClick={() => openEditor('dependency', row)}>编辑</Button>
      {row.archived_at
        ? <Button size="small" onClick={() => void api.restoreDependency(row.id, row.version).then(refresh)}>恢复</Button>
        : <Button size="small" danger onClick={() => void api.archiveDependency(row.id, row.version).then(refresh)}>归档</Button>}
    </Space> : <Tag>自动发现，只读</Tag> },
  ]

  const tabs = [
    { key: 'node', label: '节点', children: <><Button type="primary" onClick={() => openEditor('node')}>新增节点</Button><Table rowKey="id" loading={nodes.isLoading} dataSource={nodes.data?.items ?? []} columns={nodeColumns} pagination={{ pageSize: 20 }} /></> },
    { key: 'service', label: '服务', children: <><Button type="primary" onClick={() => openEditor('service')}>新增服务</Button><Table rowKey="id" loading={services.isLoading} dataSource={services.data?.items ?? []} columns={serviceColumns} pagination={{ pageSize: 20 }} /></> },
    { key: 'dependency', label: '依赖关系', children: <><Button type="primary" onClick={() => openEditor('dependency')}>新增依赖</Button><Table rowKey="id" loading={dependencies.isLoading} dataSource={dependencies.data?.items ?? []} columns={dependencyColumns} pagination={{ pageSize: 20 }} /></> },
  ]

  return <Card className="page-card" title="资源管理" extra={<Checkbox checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)}>显示已归档</Checkbox>}>
    <Tabs items={tabs} />
    <Modal open={Boolean(editor)} title={editor?.record ? '编辑资源' : '新增资源'} confirmLoading={save.isPending} onCancel={() => setEditor(null)} onOk={() => void form.validateFields().then((values) => save.mutate(values))}>
      <Form form={form} layout="vertical">
        {editor && editor.kind !== 'dependency' && !editor.record ? <Form.Item label="标识" name="id" rules={[{ required: true }]}><Input /></Form.Item> : null}
        {editor?.kind === 'node' ? <>
          <Form.Item label="显示名称" name="display_name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="描述" name="description"><Input.TextArea /></Form.Item>
          <Form.Item label="标签（逗号分隔）" name="tags"><Input /></Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked"><Switch /></Form.Item>
        </> : null}
        {editor?.kind === 'service' ? <>
          <Form.Item label="所属节点" name="node_id" rules={[{ required: true }]}><Select options={(nodes.data?.items ?? []).map((node) => ({ value: node.id, label: node.display_name }))} /></Form.Item>
          <Form.Item label="服务名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="服务类型" name="service_type" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="描述" name="description"><Input.TextArea /></Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked"><Switch /></Form.Item>
        </> : null}
        {editor?.kind === 'dependency' ? <>
          <Form.Item label="源服务" name="source_service_id" rules={[{ required: true }]}><Select options={(services.data?.items ?? []).map((service) => ({ value: service.id, label: service.name }))} /></Form.Item>
          <Form.Item label="目标服务" name="target_service_id" rules={[{ required: true }]}><Select options={(services.data?.items ?? []).map((service) => ({ value: service.id, label: service.name }))} /></Form.Item>
        </> : null}
      </Form>
    </Modal>
  </Card>
}

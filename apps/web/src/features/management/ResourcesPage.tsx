import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Checkbox, Form, Input, message, Modal, Select, Space, Switch, Table, Tabs, Tag } from 'antd'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ApiError, api } from '../../api/client'
import type { ManagedNode, Service, ServiceDependency } from '../../api/types'
import { parseTags } from './resourceForm'

type ResourceKind = 'node' | 'service' | 'dependency'

export default function ResourcesPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [includeArchived, setIncludeArchived] = useState(false)
  const [activeKind, setActiveKind] = useState<ResourceKind>(() => {
    const tab = searchParams.get('tab')
    return tab === 'services' ? 'service' : tab === 'dependencies' ? 'dependency' : 'node'
  })
  const [pages, setPages] = useState<Record<ResourceKind, { page: number; pageSize: number }>>({
    node: { page: 1, pageSize: 20 },
    service: { page: 1, pageSize: 20 },
    dependency: { page: 1, pageSize: 20 },
  })
  const [editor, setEditor] = useState<{ kind: ResourceKind; record?: ManagedNode | Service | ServiceDependency } | null>(null)
  const [candidateSearch, setCandidateSearch] = useState('')
  const [form] = Form.useForm()
  const nodeFilters = {
    status: searchParams.get('status') || undefined,
    service_type: searchParams.get('service_type') || undefined,
  }
  const nodes = useQuery({
    queryKey: ['managed-nodes', includeArchived, pages.node, nodeFilters],
    queryFn: () => api.nodes({ ...pages.node, includeArchived, ...nodeFilters }),
    enabled: activeKind === 'node',
  })
  const services = useQuery({
    queryKey: ['managed-services', includeArchived, pages.service],
    queryFn: () => api.services({ ...pages.service, includeArchived }),
    enabled: activeKind === 'service',
  })
  const dependencies = useQuery({
    queryKey: ['managed-dependencies', includeArchived, pages.dependency],
    queryFn: () => api.dependencies({ ...pages.dependency, includeArchived }),
    enabled: activeKind === 'dependency',
  })
  const nodeCandidates = useQuery({
    queryKey: ['node-candidates', candidateSearch],
    queryFn: () => api.nodes({ page: 1, pageSize: 100, q: candidateSearch }),
    enabled: editor?.kind === 'service',
  })
  const serviceCandidates = useQuery({
    queryKey: ['service-candidates', candidateSearch],
    queryFn: () => api.services({ page: 1, pageSize: 100, q: candidateSearch }),
    enabled: editor?.kind === 'dependency',
  })

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['managed-nodes'] })
    void queryClient.invalidateQueries({ queryKey: ['managed-services'] })
    void queryClient.invalidateQueries({ queryKey: ['managed-dependencies'] })
  }

  function clearNodeFilters() {
    const next = new URLSearchParams(searchParams)
    next.delete('status')
    next.delete('service_type')
    setSearchParams(next)
    setPages((previous) => ({ ...previous, node: { ...previous.node, page: 1 } }))
  }

  function changeTab(key: string) {
    const kind = key as ResourceKind
    const next = new URLSearchParams(searchParams)
    next.set('tab', kind === 'node' ? 'nodes' : kind === 'service' ? 'services' : 'dependencies')
    setSearchParams(next)
    setActiveKind(kind)
  }

  const showError = (error: unknown) => void message.error(
    error instanceof ApiError && error.status === 409
      ? '数据已被其他人更新，请刷新后重试'
      : error instanceof Error ? error.message : '操作失败',
  )

  const save = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (!editor) return
      if (editor.kind === 'node') {
        const nodeValues = { ...values, tags: parseTags(values.tags) }
        if (editor.record) {
          const node = editor.record as ManagedNode
          return api.updateNode(
            node.id,
            node.version,
            nodeValues as Parameters<typeof api.updateNode>[2],
          )
        }
        return api.createNode(nodeValues as Parameters<typeof api.createNode>[0])
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
    onError: showError,
  })

  const toggleArchive = useMutation({
    mutationFn: async ({ kind, record }: {
      kind: ResourceKind
      record: ManagedNode | Service | ServiceDependency
    }) => {
      if (kind === 'node') {
        const node = record as ManagedNode
        return node.archived_at
          ? api.restoreNode(node.id, node.version)
          : api.archiveNode(node.id, node.version)
      }
      if (kind === 'service') {
        const service = record as Service
        return service.archived_at
          ? api.restoreService(service.id, service.version)
          : api.archiveService(service.id, service.version)
      }
      const dependency = record as ServiceDependency
      return dependency.archived_at
        ? api.restoreDependency(dependency.id, dependency.version)
        : api.archiveDependency(dependency.id, dependency.version)
    },
    onSuccess: refresh,
    onError: showError,
  })

  function openEditor(kind: ResourceKind, record?: ManagedNode | Service | ServiceDependency) {
    setEditor({ kind, record })
    setCandidateSearch('')
    if (record) {
      form.setFieldsValue({ ...record, tags: 'tags' in record ? record.tags.join(',') : undefined })
    } else {
      form.resetFields()
      form.setFieldsValue({ enabled: true })
    }
  }

  function pagination(kind: ResourceKind, total: number) {
    const current = pages[kind]
    return {
      current: current.page,
      pageSize: current.pageSize,
      total,
      onChange: (page: number, pageSize: number) => setPages((previous) => ({
        ...previous,
        [kind]: { page: pageSize === current.pageSize ? page : 1, pageSize },
      })),
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
        ? <Button size="small" onClick={() => toggleArchive.mutate({ kind: 'node', record: row })}>恢复</Button>
        : <Button size="small" danger onClick={() => toggleArchive.mutate({ kind: 'node', record: row })}>归档</Button>}
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
        ? <Button size="small" onClick={() => toggleArchive.mutate({ kind: 'service', record: row })}>恢复</Button>
        : <Button size="small" danger onClick={() => toggleArchive.mutate({ kind: 'service', record: row })}>归档</Button>}
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
        ? <Button size="small" onClick={() => toggleArchive.mutate({ kind: 'dependency', record: row })}>恢复</Button>
        : <Button size="small" danger onClick={() => toggleArchive.mutate({ kind: 'dependency', record: row })}>归档</Button>}
    </Space> : <Tag>自动发现，只读</Tag> },
  ]

  const tabs = [
    { key: 'node', label: '节点', children: <><Space wrap><Button type="primary" onClick={() => openEditor('node')}>新增节点</Button>{nodeFilters.service_type || nodeFilters.status ? <><Tag color="blue">当前筛选：{[nodeFilters.service_type && `服务类型 ${nodeFilters.service_type}`, nodeFilters.status && `状态 ${nodeFilters.status}`].filter(Boolean).join('，')}</Tag><Button onClick={clearNodeFilters}>清除筛选</Button></> : null}</Space><Table rowKey="id" loading={nodes.isLoading} dataSource={nodes.data?.items ?? []} columns={nodeColumns} pagination={pagination('node', nodes.data?.total ?? 0)} /></> },
    { key: 'service', label: '服务', children: <><Button type="primary" onClick={() => openEditor('service')}>新增服务</Button><Table rowKey="id" loading={services.isLoading} dataSource={services.data?.items ?? []} columns={serviceColumns} pagination={pagination('service', services.data?.total ?? 0)} /></> },
    { key: 'dependency', label: '依赖关系', children: <><Button type="primary" onClick={() => openEditor('dependency')}>新增依赖</Button><Table rowKey="id" loading={dependencies.isLoading} dataSource={dependencies.data?.items ?? []} columns={dependencyColumns} pagination={pagination('dependency', dependencies.data?.total ?? 0)} /></> },
  ]

  return <Card className="page-card" title="资源管理" extra={<Checkbox checked={includeArchived} onChange={(event) => {
    setIncludeArchived(event.target.checked)
    setPages((previous) => ({
      node: { ...previous.node, page: 1 },
      service: { ...previous.service, page: 1 },
      dependency: { ...previous.dependency, page: 1 },
    }))
  }}>显示已归档</Checkbox>}>
    <Tabs activeKey={activeKind} onChange={changeTab} items={tabs} />
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
          <Form.Item label="所属节点" name="node_id" rules={[{ required: true }]}><Select showSearch filterOption={false} onSearch={setCandidateSearch} options={(nodeCandidates.data?.items ?? []).map((node) => ({ value: node.id, label: node.display_name }))} /></Form.Item>
          <Form.Item label="服务名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="服务类型" name="service_type" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="描述" name="description"><Input.TextArea /></Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked"><Switch /></Form.Item>
        </> : null}
        {editor?.kind === 'dependency' ? <>
          <Form.Item label="源服务" name="source_service_id" rules={[{ required: true }]}><Select showSearch filterOption={false} onSearch={setCandidateSearch} options={(serviceCandidates.data?.items ?? []).map((service) => ({ value: service.id, label: service.name }))} /></Form.Item>
          <Form.Item label="目标服务" name="target_service_id" rules={[{ required: true }]}><Select showSearch filterOption={false} onSearch={setCandidateSearch} options={(serviceCandidates.data?.items ?? []).map((service) => ({ value: service.id, label: service.name }))} /></Form.Item>
        </> : null}
      </Form>
    </Modal>
  </Card>
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Checkbox, Form, Input, message, Modal, Select, Space, Table, Tag } from 'antd'
import { useState } from 'react'

import { ApiError, api } from '../../api/client'
import type { UserAccount } from '../../api/types'

export default function UsersPage() {
  const queryClient = useQueryClient()
  const [includeArchived, setIncludeArchived] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [editing, setEditing] = useState<UserAccount | 'new' | null>(null)
  const [resetting, setResetting] = useState<UserAccount | null>(null)
  const [form] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const users = useQuery({
    queryKey: ['managed-users', includeArchived, page, pageSize],
    queryFn: () => api.users({ page, pageSize, includeArchived }),
  })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['managed-users'] })
  const showError = (error: unknown) => void message.error(
    error instanceof ApiError && error.status === 409
      ? '数据已被其他人更新，请刷新后重试'
      : error instanceof Error ? error.message : '操作失败',
  )
  const save = useMutation({
    mutationFn: (values: Record<string, unknown>) => editing === 'new'
      ? api.createUser(values as Parameters<typeof api.createUser>[0])
      : api.updateUser(
          editing!.id,
          editing!.version,
          values as Parameters<typeof api.updateUser>[2],
        ),
    onSuccess: () => {
      setEditing(null)
      form.resetFields()
      refresh()
    },
    onError: showError,
  })
  const resetPassword = useMutation({
    mutationFn: (password: string) => api.resetUserPassword(resetting!.id, resetting!.version, password),
    onSuccess: () => {
      setResetting(null)
      passwordForm.resetFields()
      refresh()
      void message.success('密码已重置，该用户的现有会话已撤销')
    },
    onError: showError,
  })
  const toggleArchive = useMutation({
    mutationFn: (row: UserAccount) => row.archived_at
      ? api.restoreUser(row.id, row.version)
      : api.archiveUser(row.id, row.version),
    onSuccess: refresh,
    onError: showError,
  })

  function open(record: UserAccount | 'new') {
    setEditing(record)
    if (record === 'new') form.resetFields()
    else form.setFieldsValue(record)
  }

  const columns = [
    { title: '用户名', dataIndex: 'username' },
    { title: '显示名', dataIndex: 'display_name' },
    { title: '角色', dataIndex: 'role', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '状态', render: (_: unknown, row: UserAccount) => <Tag color={row.is_active ? 'green' : 'default'}>{row.is_active ? '启用' : '停用'}</Tag> },
    { title: '操作', render: (_: unknown, row: UserAccount) => <Space>
      <Button size="small" onClick={() => open(row)}>编辑</Button>
      {!row.archived_at ? <Button size="small" onClick={() => setResetting(row)}>重置密码</Button> : null}
      {row.archived_at
        ? <Button size="small" onClick={() => toggleArchive.mutate(row)}>恢复</Button>
        : <Button size="small" danger onClick={() => toggleArchive.mutate(row)}>停用</Button>}
    </Space> },
  ]

  return <Card className="page-card" title="用户管理" extra={<Space><Checkbox checked={includeArchived} onChange={(event) => {
    setIncludeArchived(event.target.checked)
    setPage(1)
  }}>显示已归档</Checkbox><Button type="primary" onClick={() => open('new')}>新增用户</Button></Space>}>
    <Table rowKey="id" loading={users.isLoading} dataSource={users.data?.items ?? []} columns={columns} pagination={{
      current: page,
      pageSize,
      total: users.data?.total ?? 0,
      onChange: (nextPage, nextPageSize) => {
        setPage(nextPageSize === pageSize ? nextPage : 1)
        setPageSize(nextPageSize)
      },
    }} />
    <Modal open={Boolean(editing)} title={editing === 'new' ? '新增用户' : '编辑用户'} confirmLoading={save.isPending} onCancel={() => setEditing(null)} onOk={() => void form.validateFields().then((values) => save.mutate(values))}>
      <Form form={form} layout="vertical">
        {editing === 'new' ? <Form.Item label="用户名" name="username" rules={[{ required: true }]}><Input /></Form.Item> : null}
        <Form.Item label="显示名" name="display_name" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item label="角色" name="role" rules={[{ required: true }]}><Select options={['admin', 'operator', 'viewer'].map((value) => ({ value, label: value }))} /></Form.Item>
        {editing === 'new' ? <Form.Item label="初始密码" name="password" rules={[{ required: true, min: 12 }]}><Input.Password /></Form.Item> : null}
      </Form>
    </Modal>
    <Modal
      open={Boolean(resetting)}
      title={`重置密码：${resetting?.username ?? ''}`}
      confirmLoading={resetPassword.isPending}
      onCancel={() => setResetting(null)}
      onOk={() => void passwordForm.validateFields().then(({ password }) => resetPassword.mutate(password))}
    >
      <Form form={passwordForm} layout="vertical">
        <Form.Item label="新密码" name="password" rules={[{ required: true, min: 12 }]}>
          <Input.Password autoComplete="new-password" />
        </Form.Item>
      </Form>
    </Modal>
  </Card>
}

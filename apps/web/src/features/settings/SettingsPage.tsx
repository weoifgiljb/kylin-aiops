import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Descriptions, Space, Table, Tabs, Tag, Typography } from 'antd'

import { api } from '../../api/client'
import type { ComponentRuntimeStatus, RuntimeState } from '../../api/types'
import { useAuth } from '../auth/auth-state'

const actions = [
  ['restart_demo_service', 'app-01', '重启 Java Demo Service'],
  ['reload_nginx', 'web-01', 'nginx -t 后 reload'],
  ['stop_fault_stressor', '实验节点', '停止指定实验压力进程'],
  ['remove_fault_file', '实验节点', '删除受控 disk-fill.bin'],
  ['clear_fault_netem', 'app-01', '清理匹配实验和网卡的 netem'],
  ['terminate_fault_db_sessions', 'db-01', '终止 ops_fault 测试连接'],
].map(([name, target, description]) => ({ name, target, description }))

const statusPresentation: Record<RuntimeState, { color: string; label: string }> = {
  available: { color: 'green', label: '可用' },
  degraded: { color: 'orange', label: '降级' },
  unconfigured: { color: 'default', label: '未配置' },
  unreachable: { color: 'red', label: '不可达' },
}

/** 展示后端观测到的运行状态，并保留定位故障需要的实现信息。 */
function RuntimeStatusValue({ value }: { value: ComponentRuntimeStatus }) {
  const presentation = statusPresentation[value.status]
  const runtimeName = [value.backend, value.model].filter(Boolean).join(' / ')
  return (
    <Space orientation="vertical" size={2}>
      <Space><Tag color={presentation.color}>{presentation.label}</Tag>{runtimeName && <span>{runtimeName}</span>}</Space>
      <Typography.Text type="secondary">{value.detail}</Typography.Text>
    </Space>
  )
}

export default function SettingsPage() {
  const { user } = useAuth()
  const statusQuery = useQuery({
    queryKey: ['system-status'],
    queryFn: api.systemStatus,
    refetchInterval: 15_000,
  })

  const identity = (
    <Descriptions bordered column={1}>
      <Descriptions.Item label="当前账号">{user?.display_name || user?.username}</Descriptions.Item>
      <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
      <Descriptions.Item label="角色"><Tag color="blue">{user?.role}</Tag></Descriptions.Item>
      <Descriptions.Item label="会话安全">
        access token 仅保存在当前页面内存中，refresh token 由安全 Cookie 管理。
      </Descriptions.Item>
      <Descriptions.Item label="账号管理">账号、角色与密码由管理员统一维护。</Descriptions.Item>
    </Descriptions>
  )

  const modelStatus = statusQuery.isError
    ? <Alert type="error" showIcon title="无法读取运行状态" description="请检查 ops-api 和认证配置。" />
    : statusQuery.data
      ? (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="确定性诊断"><RuntimeStatusValue value={statusQuery.data.components.deterministic_diagnosis} /></Descriptions.Item>
            <Descriptions.Item label="MindSpore"><RuntimeStatusValue value={statusQuery.data.components.mindspore} /></Descriptions.Item>
            <Descriptions.Item label="生成式诊断"><RuntimeStatusValue value={statusQuery.data.components.generative_ai} /></Descriptions.Item>
            <Descriptions.Item label="检查时间">{new Date(statusQuery.data.checked_at).toLocaleString()}</Descriptions.Item>
          </Descriptions>
        )
      : <Card loading variant="borderless" />

  return (
    <Card className="page-card" title="系统设置">
      <Tabs items={[
        {
          key: 'nodes',
          label: '节点注册',
          children: (
            <Descriptions bordered column={1}>
              <Descriptions.Item label="注册方式">Agent 使用独立凭据主动注册，不接受人类用户 JWT</Descriptions.Item>
              <Descriptions.Item label="离线判定">最后遥测超过 30 秒</Descriptions.Item>
              <Descriptions.Item label="远程端口"><Tag color="green">不开放</Tag></Descriptions.Item>
            </Descriptions>
          ),
        },
        { key: 'model', label: '模型状态', children: modelStatus },
        {
          key: 'actions',
          label: '白名单动作',
          children: <Table rowKey="name" pagination={false} dataSource={actions} columns={[
            { title: '动作', dataIndex: 'name' },
            { title: '目标', dataIndex: 'target' },
            { title: '安全边界', dataIndex: 'description' },
          ]} />,
        },
        { key: 'permissions', label: '账号与会话', children: identity },
      ]} />
    </Card>
  )
}

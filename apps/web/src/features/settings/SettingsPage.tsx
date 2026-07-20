import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { useState } from 'react'

import { api, getToken, setToken } from '../../api/client'
import type { ComponentRuntimeStatus, RuntimeState } from '../../api/types'

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

/** Render observed runtime state and retain the backend detail needed for diagnosis. */
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
  const [token, updateToken] = useState(getToken())
  const statusQuery = useQuery({
    queryKey: ['system-status'],
    queryFn: api.systemStatus,
    refetchInterval: 15_000,
  })

  const identity = (
    <div>
      <Typography.Title level={4}>开发环境身份</Typography.Title>
      <Form layout="vertical" onFinish={() => setToken(token)}>
        <Form.Item label="角色模板">
          <Select
            value={token}
            onChange={(value) => { setToken(value); updateToken(value) }}
            options={[
              { label: '管理员', value: 'dev-admin-token' },
              { label: '运维员', value: 'dev-operator-token' },
              { label: '只读用户', value: 'dev-viewer-token' },
            ]}
          />
        </Form.Item>
        <Form.Item label="Bearer Token">
          <Space.Compact block>
            <Input.Password value={token} onChange={(event) => updateToken(event.target.value)} />
            <Button htmlType="submit" type="primary">保存</Button>
          </Space.Compact>
        </Form.Item>
      </Form>
      <Typography.Paragraph type="secondary">
        生产环境必须由统一身份服务签发 Token；页面不会信任用户自报角色。
      </Typography.Paragraph>
    </div>
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
              <Descriptions.Item label="注册方式">Agent 主动注册，生产要求 mTLS</Descriptions.Item>
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
        { key: 'permissions', label: '用户权限', children: identity },
      ]} />
    </Card>
  )
}

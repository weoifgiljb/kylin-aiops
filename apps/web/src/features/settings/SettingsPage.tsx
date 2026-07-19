import { Button, Card, Descriptions, Form, Input, Select, Space, Table, Tabs, Tag, Typography } from 'antd'
import { useState } from 'react'

import { getToken, setToken } from '../../api/client'

const actions = [
  ['restart_demo_service', 'app-01', '重启 Java Demo Service'],
  ['reload_nginx', 'web-01', 'nginx -t 后 reload'],
  ['stop_fault_stressor', '实验节点', '停止指定实验压力进程'],
  ['remove_fault_file', '实验节点', '删除受控 disk-fill.bin'],
  ['clear_fault_netem', 'app-01', '清理匹配实验和网卡的 netem'],
  ['terminate_fault_db_sessions', 'db-01', '终止 ops_fault 测试连接'],
].map(([name, target, description]) => ({ name, target, description }))

export default function SettingsPage() {
  const [token, updateToken] = useState(getToken())
  const identity = <div><Typography.Title level={4}>开发环境身份</Typography.Title><Form layout="vertical" onFinish={() => setToken(token)}><Form.Item label="角色模板"><Select value={token} onChange={(value) => { setToken(value); updateToken(value) }} options={[{ label: '管理员', value: 'dev-admin-token' }, { label: '运维员', value: 'dev-operator-token' }, { label: '只读用户', value: 'dev-viewer-token' }]} /></Form.Item><Form.Item label="Bearer Token"><Space.Compact block><Input.Password value={token} onChange={(event) => updateToken(event.target.value)} /><Button htmlType="submit" type="primary">保存</Button></Space.Compact></Form.Item></Form><Typography.Paragraph type="secondary">生产环境必须由统一身份服务签发 Token；页面不会信任用户自报角色。</Typography.Paragraph></div>
  return <Card className="page-card" title="系统设置"><Tabs items={[
    { key: 'nodes', label: '节点注册', children: <Descriptions bordered column={1}><Descriptions.Item label="注册方式">Agent 主动注册，生产要求 mTLS</Descriptions.Item><Descriptions.Item label="离线判定">最后遥测超过 30 秒</Descriptions.Item><Descriptions.Item label="远程端口"><Tag color="green">不开放</Tag></Descriptions.Item></Descriptions> },
    { key: 'model', label: '模型状态', children: <Descriptions bordered column={1}><Descriptions.Item label="确定性诊断"><Tag color="green">可用</Tag></Descriptions.Item><Descriptions.Item label="MindSpore">未加载 checkpoint 时自动降级</Descriptions.Item><Descriptions.Item label="MindIE">不可用时返回规则与拓扑诊断</Descriptions.Item><Descriptions.Item label="验收要求">Ascend device_target、npu-smi、模型 SHA-256 与盲测报告</Descriptions.Item></Descriptions> },
    { key: 'actions', label: '白名单动作', children: <Table rowKey="name" pagination={false} dataSource={actions} columns={[{ title: '动作', dataIndex: 'name' }, { title: '目标', dataIndex: 'target' }, { title: '安全边界', dataIndex: 'description' }]} /> },
    { key: 'permissions', label: '用户权限', children: identity },
  ]} /></Card>
}

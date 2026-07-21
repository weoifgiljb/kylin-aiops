import {
  AuditOutlined,
  BellOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  LogoutOutlined,
  MessageOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Button, Layout, Menu, Typography } from 'antd'
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { api } from '../api/client'
import type { CurrentUser } from '../api/types'

const { Header, Sider, Content } = Layout

const productItems = [
  { key: '/', icon: <DashboardOutlined />, label: <Link to="/">态势总览</Link> },
  { key: '/incidents', icon: <BellOutlined />, label: <Link to="/incidents">事件中心</Link> },
  { key: '/chat', icon: <MessageOutlined />, label: <Link to="/chat">智能问答</Link> },
  { key: '/evaluation', icon: <ExperimentOutlined />, label: <Link to="/evaluation">评测报告</Link> },
  { key: '/settings', icon: <SettingOutlined />, label: <Link to="/settings">系统设置</Link> },
]

const adminItems = [
  { key: '/management/resources', icon: <DatabaseOutlined />, label: <Link to="/management/resources">资源管理</Link> },
  { key: '/management/users', icon: <TeamOutlined />, label: <Link to="/management/users">用户管理</Link> },
  { key: '/management/audit', icon: <AuditOutlined />, label: <Link to="/management/audit">审计日志</Link> },
]

interface AppShellProps {
  children: ReactNode
  user: CurrentUser
  onLogout: () => void
}

export function AppShell({ children, user, onLogout }: AppShellProps) {
  const location = useLocation()
  const statusQuery = useQuery({
    queryKey: ['system-status'],
    queryFn: api.systemStatus,
    refetchInterval: 15_000,
  })
  const diagnosisState = statusQuery.data?.components.deterministic_diagnosis.status
  const diagnosisLabel = statusQuery.isError
    ? '状态接口不可达'
    : diagnosisState === 'available'
      ? '规则诊断可用'
      : '状态检查中'
  const menuItems = user.role === 'admin' ? [...productItems, ...adminItems] : productItems

  return (
    <Layout className="app-layout">
      <Sider width={216} className="app-sidebar" breakpoint="lg" collapsedWidth={72}>
        <div className="brand"><span className="brand-mark">K</span><span>麒麟智维</span></div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={3}>银河麒麟智能运维</Typography.Title>
          <div className="header-actions">
            <div className="operator">
              <span className="health-dot" data-status={statusQuery.isError ? 'unreachable' : diagnosisState ?? 'checking'} />
              {diagnosisLabel}
            </div>
            <span className="current-user">{user.display_name} · {user.role}</span>
            <Button type="text" icon={<LogoutOutlined />} onClick={onLogout}>退出</Button>
          </div>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  )
}

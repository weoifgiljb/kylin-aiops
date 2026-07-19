import {
  BellOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  MessageOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { Layout, Menu, Typography } from 'antd'
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: <Link to="/">态势总览</Link> },
  { key: '/incidents', icon: <BellOutlined />, label: <Link to="/incidents">事件中心</Link> },
  { key: '/chat', icon: <MessageOutlined />, label: <Link to="/chat">智能问答</Link> },
  { key: '/evaluation', icon: <ExperimentOutlined />, label: <Link to="/evaluation">评测报告</Link> },
  { key: '/settings', icon: <SettingOutlined />, label: <Link to="/settings">系统设置</Link> },
]

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  return (
    <Layout className="app-layout">
      <Sider width={216} className="app-sidebar" breakpoint="lg" collapsedWidth={72}>
        <div className="brand"><span className="brand-mark">K</span><span>麒麟智维</span></div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={3}>银河麒麟智能运维</Typography.Title>
          <div className="operator"><span className="health-dot" />确定性诊断在线</div>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  )
}

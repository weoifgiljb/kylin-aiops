import { App as AntApp, ConfigProvider, Result } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { useAuth } from '../features/auth/auth-state'
import LoginPage from '../features/auth/LoginPage'
import { EventStreamBridge } from './EventStreamBridge'

const OverviewPage = lazy(() => import('../features/overview/OverviewPage'))
const IncidentsPage = lazy(() => import('../features/incidents/IncidentsPage'))
const ChatPage = lazy(() => import('../features/chat/ChatPage'))
const EvaluationPage = lazy(() => import('../features/evaluation/EvaluationPage'))
const SettingsPage = lazy(() => import('../features/settings/SettingsPage'))
const ResourcesPage = lazy(() => import('../features/management/ResourcesPage'))
const UsersPage = lazy(() => import('../features/management/UsersPage'))
const AuditPage = lazy(() => import('../features/management/AuditPage'))

export function App() {
  const auth = useAuth()
  const theme = { token: { colorPrimary: '#1769e0', borderRadius: 6, fontFamily: 'Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif' } }

  if (auth.loading) return <div className="loading-screen">正在验证登录状态…</div>
  if (!auth.user) return <ConfigProvider theme={theme}><AntApp><LoginPage onLogin={auth.login} /></AntApp></ConfigProvider>

  const adminOnly = (element: React.ReactNode) => auth.user?.role === 'admin'
    ? element
    : <Result status="403" title="403" subTitle="当前账号无权访问此页面" />

  return (
    <ConfigProvider theme={theme}>
      <AntApp>
        <AppShell user={auth.user} onLogout={() => void auth.logout()}>
          <EventStreamBridge />
          <Suspense fallback={<div className="loading-screen">正在加载…</div>}>
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/incidents" element={<IncidentsPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/evaluation" element={<EvaluationPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/management/resources" element={adminOnly(<ResourcesPage />)} />
              <Route path="/management/users" element={adminOnly(<UsersPage />)} />
              <Route path="/management/audit" element={adminOnly(<AuditPage />)} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AppShell>
      </AntApp>
    </ConfigProvider>
  )
}

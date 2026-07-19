import { App as AntApp, ConfigProvider } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { EventStreamBridge } from './EventStreamBridge'

const OverviewPage = lazy(() => import('../features/overview/OverviewPage'))
const IncidentsPage = lazy(() => import('../features/incidents/IncidentsPage'))
const ChatPage = lazy(() => import('../features/chat/ChatPage'))
const EvaluationPage = lazy(() => import('../features/evaluation/EvaluationPage'))
const SettingsPage = lazy(() => import('../features/settings/SettingsPage'))

export function App() {
  return <ConfigProvider theme={{ token: { colorPrimary: '#1769e0', borderRadius: 6, fontFamily: 'Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif' } }}><AntApp><AppShell><EventStreamBridge /><Suspense fallback={<div className="loading-screen">正在加载…</div>}><Routes><Route path="/" element={<OverviewPage />} /><Route path="/incidents" element={<IncidentsPage />} /><Route path="/chat" element={<ChatPage />} /><Route path="/evaluation" element={<EvaluationPage />} /><Route path="/settings" element={<SettingsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense></AppShell></AntApp></ConfigProvider>
}

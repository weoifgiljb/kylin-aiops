import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Descriptions, Progress } from 'antd'

import { api } from '../../api/client'

const labels: Record<string, string> = { detection_f1: '异常检测 F1', severity_macro_f1: '严重度 Macro-F1', root_cause_top1: '根因 Top-1', root_cause_top3: '根因 Top-3', propagation_edge_f1: '传播路径边 F1', remediation_success_rate: '修复成功率' }

export default function EvaluationPage() {
  const { data } = useQuery({ queryKey: ['evaluation', 'demo-run'], queryFn: () => api.evaluation('demo-run') })
  if (!data) return <Card loading />
  const hasTrials = data.trial_count > 0
  return <Card className="page-card" title="量化评测"><Alert type={hasTrials ? (data.status === 'passed' ? 'success' : 'error') : 'warning'} showIcon title={hasTrials ? `已加载 ${data.trial_count} 次盲测：${data.status}` : '当前仅加载验收门槛；真实指标必须由 120 次盲测生成。'} /><Descriptions column={1} bordered className="evaluation-list">{Object.entries(data.thresholds).map(([key, threshold]) => { const actual = data.metrics[key]; return <Descriptions.Item key={key} label={labels[key] ?? key}><Progress percent={(actual ?? threshold) * 100} status={actual !== undefined && actual < threshold ? 'exception' : 'normal'} format={(percent) => actual === undefined ? `门槛 ${percent}%` : `实测 ${percent}% / 门槛 ${threshold * 100}%`} /></Descriptions.Item> })}</Descriptions></Card>
}

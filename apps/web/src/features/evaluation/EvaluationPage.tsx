import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Descriptions, Empty, Progress, Select, Space, Typography } from 'antd'
import { useState } from 'react'

import { api } from '../../api/client'
import type { EvaluationRun } from '../../api/types'

const labels: Record<string, string> = {
  detection_f1: '异常检测 F1',
  severity_macro_f1: '严重度 Macro-F1',
  root_cause_top1: '根因 Top-1',
  root_cause_top3: '根因 Top-3',
  propagation_edge_f1: '传播路径边 F1',
  remediation_success_rate: '修复成功率',
}

function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** Render report metrics without substituting an acceptance threshold for missing evidence. */
function MetricResult({ actual, threshold }: { actual: number | undefined; threshold: number }) {
  if (actual === undefined) {
    return (
      <Typography.Text type="secondary">
        报告未提供实测值 / 门槛 {percentage(threshold)}
      </Typography.Text>
    )
  }

  return (
    <Progress
      percent={actual * 100}
      status={actual >= threshold ? 'success' : 'exception'}
      format={() => `实测 ${percentage(actual)} / 门槛 ${percentage(threshold)}`}
    />
  )
}

function ReportDetails({ run }: { run: EvaluationRun }) {
  const statusText = run.status === 'passed' ? '通过' : '未通过'

  return (
    <>
      <Alert
        type={run.status === 'passed' ? 'success' : 'error'}
        showIcon
        title={`已加载 ${run.id}：${run.trial_count} 次盲测，${statusText}`}
      />
      <Descriptions column={1} bordered className="evaluation-list">
        {Object.entries(run.thresholds).map(([key, threshold]) => (
          <Descriptions.Item key={key} label={labels[key] ?? key}>
            <MetricResult actual={run.metrics[key]} threshold={threshold} />
          </Descriptions.Item>
        ))}
      </Descriptions>
    </>
  )
}

export default function EvaluationPage() {
  const [selectedRunId, setSelectedRunId] = useState<string>()
  const query = useQuery({
    queryKey: ['evaluation-runs'],
    queryFn: api.evaluations,
    refetchInterval: 30_000,
  })

  if (query.isLoading) return <Card loading />
  if (query.isError) {
    return (
      <Card className="page-card" title="量化评测">
        <Alert type="error" showIcon title="评测报告接口不可达" />
      </Card>
    )
  }

  const runs = query.data?.items ?? []
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0]

  return (
    <Card
      className="page-card"
      title="量化评测"
      extra={selectedRun ? (
        <Space>
          <Typography.Text type="secondary">评测批次</Typography.Text>
          <Select
            aria-label="评测批次"
            value={selectedRun.id}
            options={runs.map((run) => ({ label: run.id, value: run.id }))}
            onChange={setSelectedRunId}
            style={{ minWidth: 220 }}
          />
        </Space>
      ) : undefined}
    >
      {selectedRun ? (
        <ReportDetails run={selectedRun} />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无真实评测结果"
        >
          <Typography.Text type="secondary">
            运行盲测报告生成程序，并将 report.json 输出到 EVALUATION_REPORT_DIR 下的批次目录。
          </Typography.Text>
        </Empty>
      )}
    </Card>
  )
}

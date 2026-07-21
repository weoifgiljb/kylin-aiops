import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'

interface LoginPageProps {
  onLogin: (username: string, password: string) => Promise<void>
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(values: { username: string; password: string }) {
    setSubmitting(true)
    setError(null)
    try {
      await onLogin(values.username, values.password)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '登录失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <Card className="login-card">
        <div className="login-brand"><span className="brand-mark">K</span></div>
        <Typography.Title level={2}>麒麟智能运维</Typography.Title>
        <Typography.Paragraph type="secondary">校内测试管理控制台</Typography.Paragraph>
        {error ? <Alert type="error" showIcon message={error} /> : null}
        <Form layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input autoComplete="username" prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password autoComplete="current-password" prefix={<LockOutlined />} />
          </Form.Item>
          <Button block type="primary" htmlType="submit" loading={submitting}>登录</Button>
        </Form>
      </Card>
    </main>
  )
}

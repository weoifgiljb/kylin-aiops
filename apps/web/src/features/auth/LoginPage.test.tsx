import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import LoginPage from './LoginPage'

test('submits username and password without storing them in the browser', async () => {
  const onLogin = vi.fn().mockResolvedValue(undefined)
  render(<LoginPage onLogin={onLogin} />)

  fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'admin' } })
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'a-secure-password' } })
  fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }))

  await waitFor(() => expect(onLogin).toHaveBeenCalledWith('admin', 'a-secure-password'))
  expect(localStorage.getItem('kylin_aiops_token')).toBeNull()
})

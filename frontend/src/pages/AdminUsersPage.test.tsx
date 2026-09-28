import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AdminUsersPage } from './AdminUsersPage'
import * as adminApi from '../api/admin'
import type { User } from '../types'

vi.mock('../api/admin')

const users: User[] = [
  { id: 1, username: 'alice', display_name: 'Alice', role: 'ADMIN', created_at: '2026-01-01T00:00:00Z' },
  { id: 2, username: 'bob', display_name: 'Bob', role: 'MEMBER', created_at: '2026-01-01T00:00:00Z' },
]

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminUsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminUsersPage', () => {
  it('lists existing users with their role', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(users)

    renderPage()

    expect(await screen.findByText('alice')).toBeInTheDocument()
    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(screen.getByLabelText('Role for alice')).toHaveValue('ADMIN')
    expect(screen.getByLabelText('Role for bob')).toHaveValue('MEMBER')
  })

  it('creates a new user with the chosen role', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(users)
    vi.mocked(adminApi.createUser).mockResolvedValue({
      id: 3,
      username: 'carol',
      display_name: 'Carol',
      role: 'MEMBER',
      created_at: '2026-01-01T00:00:00Z',
    })
    renderPage()
    await screen.findByText('alice')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText(/^username/i), 'carol')
    await user.type(screen.getByLabelText(/display name/i), 'Carol')
    await user.type(screen.getByLabelText(/^password/i), 'a password')
    await user.click(screen.getByRole('button', { name: /create/i }))

    await waitFor(() => expect(adminApi.createUser).toHaveBeenCalled())
    const [payload] = vi.mocked(adminApi.createUser).mock.calls[0]
    expect(payload).toMatchObject({ username: 'carol', display_name: 'Carol' })
  })

  it('promotes a member to admin', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(users)
    vi.mocked(adminApi.updateUser).mockResolvedValue({ ...users[1], role: 'ADMIN' })
    renderPage()
    await screen.findByText('bob')
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText(/role for bob/i), 'ADMIN')

    await waitFor(() => expect(adminApi.updateUser).toHaveBeenCalled())
    const [id, payload] = vi.mocked(adminApi.updateUser).mock.calls[0]
    expect(id).toBe(2)
    expect(payload).toEqual({ role: 'ADMIN' })
  })

  it('deletes a user after confirmation', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(users)
    vi.mocked(adminApi.deleteUser).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText('bob')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /delete bob/i }))

    await waitFor(() => expect(adminApi.deleteUser).toHaveBeenCalled())
    expect(vi.mocked(adminApi.deleteUser).mock.calls[0][0]).toBe(2)
  })

  it('shows a server error (e.g. last-admin protection) instead of crashing', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(users)
    vi.mocked(adminApi.deleteUser).mockRejectedValue(new Error('cannot delete the only remaining admin'))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText('alice')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /delete alice/i }))

    expect(await screen.findByText(/cannot delete the only remaining admin/i)).toBeInTheDocument()
  })
})

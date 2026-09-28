import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from './AuthContext'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function Probe() {
  const { isAuthenticated, isAdmin, user, login, logout } = useAuth()
  return (
    <div>
      <p>authenticated: {String(isAuthenticated)}</p>
      <p>admin: {String(isAdmin)}</p>
      <p>username: {user?.username ?? 'none'}</p>
      <button onClick={() => login('alice', 'a password')}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches the current user (including role) after a successful login', async () => {
    const fetchMock = fetch as ReturnType<typeof vi.fn>
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ access_token: 'abc' }))
      .mockResolvedValueOnce(
        jsonResponse({ id: 1, username: 'alice', display_name: 'Alice', role: 'ADMIN', created_at: 'x' }),
      )
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    const user = userEvent.setup()

    await user.click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByText('authenticated: true')).toBeInTheDocument())
    expect(screen.getByText('admin: true')).toBeInTheDocument()
    expect(screen.getByText('username: alice')).toBeInTheDocument()
  })

  it('exposes isAdmin=false for a MEMBER', async () => {
    const fetchMock = fetch as ReturnType<typeof vi.fn>
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ access_token: 'abc' }))
      .mockResolvedValueOnce(
        jsonResponse({ id: 2, username: 'alice', display_name: 'Alice', role: 'MEMBER', created_at: 'x' }),
      )
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    const user = userEvent.setup()

    await user.click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByText('admin: false')).toBeInTheDocument())
  })

  it('clears user state on logout', async () => {
    const fetchMock = fetch as ReturnType<typeof vi.fn>
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ access_token: 'abc' }))
      .mockResolvedValueOnce(
        jsonResponse({ id: 1, username: 'alice', display_name: 'Alice', role: 'ADMIN', created_at: 'x' }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    const user = userEvent.setup()
    await user.click(screen.getByText('login'))
    await waitFor(() => expect(screen.getByText('authenticated: true')).toBeInTheDocument())

    await user.click(screen.getByText('logout'))

    await waitFor(() => expect(screen.getByText('authenticated: false')).toBeInTheDocument())
    expect(screen.getByText('username: none')).toBeInTheDocument()
  })
})

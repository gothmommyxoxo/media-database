import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from './LoginPage'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Collection Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('navigates to the collection on successful login', async () => {
    // mockImplementation (not mockResolvedValue) so a fresh Response is built per call --
    // login() reads two responses (/auth/login then /auth/me), and a Response body can only be
    // read once.
    ;(fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) =>
      Promise.resolve(
        url.includes('/auth/me')
          ? jsonResponse({ id: 1, username: 'alice', display_name: 'Alice', role: 'MEMBER', created_at: 'x' })
          : jsonResponse({ access_token: 'abc' }),
      ),
    )
    renderLoginPage()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText(/username/i), 'alice')
    await user.type(screen.getByLabelText(/password/i), 'a password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => expect(screen.getByText('Collection Home')).toBeInTheDocument())
  })

  it('shows the server error message on invalid credentials', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ detail: 'invalid username or password' }, 401),
    )
    renderLoginPage()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText(/username/i), 'alice')
    await user.type(screen.getByLabelText(/password/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument()
  })
})

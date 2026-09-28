import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { createUser, deleteUser, listUsers, resetPassword, updateUser } from '../api/admin'
import { ApiError } from '../api/client'
import type { Role } from '../types'

export function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [newUser, setNewUser] = useState({ username: '', display_name: '', password: '', role: 'MEMBER' as Role })

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => listUsers(),
  })

  function invalidate() {
    return queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
  }

  function reportError(err: unknown) {
    setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Something went wrong.')
  }

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      setNewUser({ username: '', display_name: '', password: '', role: 'MEMBER' })
      invalidate()
    },
    onError: reportError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) => updateUser(id, { role }),
    onSuccess: invalidate,
    onError: reportError,
  })

  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, newPassword }: { id: number; newPassword: string }) => resetPassword(id, newPassword),
    onError: reportError,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: invalidate,
    onError: reportError,
  })

  function handleCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    createMutation.mutate(newUser)
  }

  function handleDelete(id: number, username: string) {
    if (!window.confirm(`Delete ${username}? This cannot be undone.`)) return
    setError(null)
    deleteMutation.mutate(id)
  }

  function handleResetPassword(id: number, username: string) {
    const newPassword = window.prompt(`New password for ${username}:`)
    if (!newPassword) return
    setError(null)
    resetPasswordMutation.mutate({ id, newPassword })
  }

  return (
    <div className="admin-users-page">
      <p>
        <Link to="/">&larr; Back to collection</Link> · <Link to="/admin/barcode-cache">Barcode cache</Link>
      </p>
      <h1>Household accounts</h1>

      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}

      <form onSubmit={handleCreate} className="create-user-form">
        <h2>Add account</h2>
        <label htmlFor="new-username">Username</label>
        <input
          id="new-username"
          value={newUser.username}
          onChange={(e) => setNewUser((u) => ({ ...u, username: e.target.value }))}
          required
        />

        <label htmlFor="new-display-name">Display name</label>
        <input
          id="new-display-name"
          value={newUser.display_name}
          onChange={(e) => setNewUser((u) => ({ ...u, display_name: e.target.value }))}
          required
        />

        <label htmlFor="new-password">Password</label>
        <input
          id="new-password"
          type="password"
          value={newUser.password}
          onChange={(e) => setNewUser((u) => ({ ...u, password: e.target.value }))}
          required
        />

        <label htmlFor="new-role">Role</label>
        <select
          id="new-role"
          value={newUser.role}
          onChange={(e) => setNewUser((u) => ({ ...u, role: e.target.value as Role }))}
        >
          <option value="MEMBER">Member</option>
          <option value="ADMIN">Admin</option>
        </select>

        <button type="submit" disabled={createMutation.isPending}>
          Create account
        </button>
      </form>

      <h2>Existing accounts</h2>
      {isLoading && <p>Loading…</p>}
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Display name</th>
            <th>Role</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users?.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td>{u.display_name}</td>
              <td>
                <select
                  aria-label={`Role for ${u.username}`}
                  value={u.role}
                  onChange={(e) => {
                    setError(null)
                    updateMutation.mutate({ id: u.id, role: e.target.value as Role })
                  }}
                >
                  <option value="MEMBER">MEMBER</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
              </td>
              <td>
                <button type="button" onClick={() => handleResetPassword(u.id, u.username)}>
                  Reset password
                </button>
                <button type="button" onClick={() => handleDelete(u.id, u.username)}>
                  {`Delete ${u.username}`}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

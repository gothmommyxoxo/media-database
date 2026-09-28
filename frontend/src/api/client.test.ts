import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, ApiError, setAccessToken, getAccessToken } from './client'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('apiFetch', () => {
  beforeEach(() => {
    setAccessToken(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches the Authorization header when an access token is set', async () => {
    setAccessToken('token-123')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/items')

    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer token-123')
  })

  it('does not send an Authorization header when no token is set', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/items')

    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).has('Authorization')).toBe(false)
  })

  it('on a 401, refreshes the token once and retries the original request', async () => {
    setAccessToken('expired-token')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401)) // original request
      .mockResolvedValueOnce(jsonResponse({ access_token: 'new-token' })) // refresh call
      .mockResolvedValueOnce(jsonResponse({ items: [] })) // retried request
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiFetch<{ items: unknown[] }>('/items')

    expect(result).toEqual({ items: [] })
    expect(getAccessToken()).toBe('new-token')
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const refreshCall = fetchMock.mock.calls[1]
    expect(refreshCall[0]).toContain('/auth/refresh')
  })

  it('throws ApiError with the server detail message on failure', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: 'item not found' }, 404))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/items/999')).rejects.toMatchObject(
      new ApiError(404, 'item not found'),
    )
  })

  it('does not attempt to refresh when the login request itself returns 401', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: 'invalid username or password' }, 401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/auth/login', { method: 'POST' })).rejects.toThrow()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('returns undefined for a 204 No Content response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiFetch('/items/1')

    expect(result).toBeUndefined()
  })
})

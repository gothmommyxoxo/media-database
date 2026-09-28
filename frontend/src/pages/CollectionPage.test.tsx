import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CollectionPage } from './CollectionPage'
import * as collectionApi from '../api/collection'
import { useAuth } from '../auth/AuthContext'
import type { MediaItem } from '../types'

vi.mock('../api/collection')
vi.mock('../auth/AuthContext')

function mockAuth(isAdmin: boolean) {
  vi.mocked(useAuth).mockReturnValue({
    isAuthenticated: true,
    isAdmin,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

const items: MediaItem[] = [
  {
    id: 1,
    media_type: 'CD',
    title: 'Discovery',
    subtitle: null,
    barcode: '724384960650',
    format: null,
    condition: null,
    notes: null,
    cover_image_url: null,
    attributes: { artist: 'Daft Punk' },
    external_ids: {},
    source: 'MANUAL',
    added_by: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    media_type: 'MANGA',
    title: 'Berserk Volume 1',
    subtitle: null,
    barcode: null,
    format: null,
    condition: null,
    notes: null,
    cover_image_url: null,
    attributes: {},
    external_ids: {},
    source: 'MANUAL',
    added_by: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CollectionPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CollectionPage', () => {
  it('renders items returned by the API', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.listItems).mockResolvedValue({ items, total: 2 })

    renderPage()

    expect(await screen.findByText('Discovery')).toBeInTheDocument()
    expect(screen.getByText('Berserk Volume 1')).toBeInTheDocument()
  })

  it('re-queries with a search term when the member types in the search box', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.listItems).mockResolvedValue({ items, total: 2 })
    renderPage()
    await screen.findByText('Discovery')
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText(/search/i), 'berserk')

    await waitFor(() =>
      expect(collectionApi.listItems).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: 'berserk' }),
      ),
    )
  })

  it('shows an empty state when there are no items', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.listItems).mockResolvedValue({ items: [], total: 0 })

    renderPage()

    expect(await screen.findByText(/no items/i)).toBeInTheDocument()
  })

  it('shows the admin nav link for an admin', async () => {
    mockAuth(true)
    vi.mocked(collectionApi.listItems).mockResolvedValue({ items: [], total: 0 })

    renderPage()

    expect(await screen.findByRole('link', { name: /admin/i })).toBeInTheDocument()
  })

  it('does not render any admin nav link for a non-admin', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.listItems).mockResolvedValue({ items: [], total: 0 })

    renderPage()

    await screen.findByText(/no items/i)
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
  })
})

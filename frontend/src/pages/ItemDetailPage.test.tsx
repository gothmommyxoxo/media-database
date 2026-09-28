import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ItemDetailPage } from './ItemDetailPage'
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

const item: MediaItem = {
  id: 1,
  media_type: 'DVD',
  title: 'Brazil',
  subtitle: null,
  barcode: '012345678905',
  format: null,
  condition: null,
  notes: null,
  cover_image_url: null,
  attributes: { director: 'Terry Gilliam' },
  external_ids: {},
  source: 'MANUAL',
  added_by: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/items/1']}>
        <Routes>
          <Route path="/items/:id" element={<ItemDetailPage />} />
          <Route path="/" element={<div>Collection Home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ItemDetailPage', () => {
  it('renders the item title and attributes', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)

    renderPage()

    expect(await screen.findByText('Brazil')).toBeInTheDocument()
    expect(screen.getByText(/terry gilliam/i)).toBeInTheDocument()
  })

  it('deletes the item after confirmation and returns to the collection', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)
    vi.mocked(collectionApi.deleteItem).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText('Brazil')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /delete/i }))

    await waitFor(() => expect(collectionApi.deleteItem).toHaveBeenCalledWith(1))
    expect(await screen.findByText('Collection Home')).toBeInTheDocument()
  })

  it('does not delete when the member cancels the confirmation', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await screen.findByText('Brazil')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /delete/i }))

    expect(collectionApi.deleteItem).not.toHaveBeenCalled()
  })

  it('shows an admin-edit link for an admin', async () => {
    mockAuth(true)
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)

    renderPage()

    expect(await screen.findByRole('link', { name: /admin edit/i })).toBeInTheDocument()
  })

  it('does not show an admin-edit link for a non-admin', async () => {
    mockAuth(false)
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)

    renderPage()

    await screen.findByText('Brazil')
    expect(screen.queryByRole('link', { name: /admin edit/i })).not.toBeInTheDocument()
  })
})

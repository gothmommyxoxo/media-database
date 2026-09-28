import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AdminItemEditPage } from './AdminItemEditPage'
import * as adminApi from '../api/admin'
import * as collectionApi from '../api/collection'
import type { MediaItem } from '../types'

vi.mock('../api/admin')
vi.mock('../api/collection')

const item: MediaItem = {
  id: 5,
  media_type: 'DVD',
  title: 'Brazil',
  subtitle: null,
  barcode: '012345678905',
  format: null,
  condition: null,
  notes: null,
  cover_image_url: null,
  attributes: { director: 'Terry Gilliam' },
  external_ids: { tmdb: '68' },
  source: 'MANUAL',
  added_by: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/items/5']}>
        <Routes>
          <Route path="/admin/items/:id" element={<AdminItemEditPage />} />
          <Route path="/items/:id" element={<div>Item Detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminItemEditPage', () => {
  it('pre-fills admin-only fields not present on the member edit form', async () => {
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)

    renderPage()

    await screen.findByDisplayValue('Brazil')
    expect(screen.getByLabelText(/source/i)).toHaveValue('MANUAL')
    expect(screen.getByLabelText(/added_by/i)).toHaveValue(3)
    expect(screen.getByLabelText(/external_ids/i)).toHaveValue(JSON.stringify(item.external_ids, null, 2))
  })

  it('submits the full admin field set, including reassigning added_by', async () => {
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)
    vi.mocked(adminApi.updateItemAdmin).mockResolvedValue({ ...item, added_by: null })
    renderPage()
    const user = userEvent.setup()
    await screen.findByDisplayValue('Brazil')

    await user.clear(screen.getByLabelText(/added_by/i))
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => expect(adminApi.updateItemAdmin).toHaveBeenCalled())
    const [id, payload] = vi.mocked(adminApi.updateItemAdmin).mock.calls[0]
    expect(id).toBe(5)
    expect(payload.added_by).toBeNull()
    expect(await screen.findByText('Item Detail')).toBeInTheDocument()
  })

  it('shows a validation error from the server without crashing', async () => {
    vi.mocked(collectionApi.getItem).mockResolvedValue(item)
    vi.mocked(adminApi.updateItemAdmin).mockRejectedValue(new Error('attributes do not match media_type'))
    renderPage()
    const user = userEvent.setup()
    await screen.findByDisplayValue('Brazil')

    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(await screen.findByText(/attributes do not match media_type/i)).toBeInTheDocument()
  })
})

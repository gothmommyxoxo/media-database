import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ManualEntryPage } from './ManualEntryPage'
import * as collectionApi from '../api/collection'
import type { MediaItem } from '../types'

vi.mock('../api/collection')

function renderPage(initialEntry = '/items/new') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/items/new" element={<ManualEntryPage />} />
          <Route path="/items/:id/edit" element={<ManualEntryPage />} />
          <Route path="/items/:id" element={<div>Item Detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ManualEntryPage - create', () => {
  it('creates an item with the chosen media type and title, then navigates to its detail page', async () => {
    vi.mocked(collectionApi.createItem).mockResolvedValue({ id: 42 } as MediaItem)
    renderPage()
    const user = userEvent.setup()

    await user.selectOptions(screen.getByLabelText(/media type/i), 'VINYL')
    await user.type(screen.getByLabelText(/^title/i), 'Random Access Memories')
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() =>
      expect(collectionApi.createItem).toHaveBeenCalledWith(
        expect.objectContaining({ media_type: 'VINYL', title: 'Random Access Memories' }),
      ),
    )
    expect(await screen.findByText('Item Detail')).toBeInTheDocument()
  })

  it('requires a title before submitting', async () => {
    renderPage()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(collectionApi.createItem).not.toHaveBeenCalled()
  })
})

describe('ManualEntryPage - edit', () => {
  const existing: MediaItem = {
    id: 7,
    media_type: 'DVD',
    title: 'Brazil',
    subtitle: null,
    barcode: null,
    format: null,
    condition: null,
    notes: 'Criterion edition',
    cover_image_url: null,
    attributes: {},
    external_ids: {},
    source: 'MANUAL',
    added_by: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  it('pre-fills the form with the existing item and submits an update', async () => {
    vi.mocked(collectionApi.getItem).mockResolvedValue(existing)
    vi.mocked(collectionApi.updateItem).mockResolvedValue(existing)
    renderPage('/items/7/edit')
    const user = userEvent.setup()

    expect(await screen.findByDisplayValue('Brazil')).toBeInTheDocument()

    await user.clear(screen.getByLabelText(/notes/i))
    await user.type(screen.getByLabelText(/notes/i), 'Updated notes')
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() =>
      expect(collectionApi.updateItem).toHaveBeenCalledWith(
        7,
        expect.objectContaining({ notes: 'Updated notes' }),
      ),
    )
  })
})

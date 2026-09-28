import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ResolutionPage } from './ResolutionPage'
import * as barcodeApi from '../api/barcode'
import type { MediaItem, ResolutionResult } from '../types'

vi.mock('../api/barcode')

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/resolve/724384960650']}>
        <Routes>
          <Route path="/resolve/:barcode" element={<ResolutionPage />} />
          <Route path="/items/:id" element={<div>Item Detail</div>} />
          <Route path="/items/new" element={<div>Manual Entry</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ResolutionPage', () => {
  it('shows an already-owned warning before the candidate list', async () => {
    const owned = { id: 5, title: 'Discovery' } as MediaItem
    const result: ResolutionResult = {
      candidates: [
        {
          source_provider: 'musicbrainz',
          media_type: 'CD',
          title: 'Discovery',
          subtitle: 'Daft Punk',
          external_id: 'abc',
          external_url: null,
          cover_image_url: null,
          raw_attributes: {},
        },
      ],
      owned_matches: [owned],
      requires_manual_entry: false,
    }
    vi.mocked(barcodeApi.resolveBarcode).mockResolvedValue(result)

    renderPage()

    expect(await screen.findByText(/already own this/i)).toBeInTheDocument()
  })

  it('shows every candidate and lets the member select one to add', async () => {
    const result: ResolutionResult = {
      candidates: [
        {
          source_provider: 'musicbrainz',
          media_type: 'CD',
          title: 'Discovery',
          subtitle: 'Daft Punk',
          external_id: 'abc',
          external_url: null,
          cover_image_url: null,
          raw_attributes: {},
        },
        {
          source_provider: 'some_other_provider',
          media_type: 'VIDEO_GAME',
          title: 'Unrelated collided item',
          subtitle: null,
          external_id: 'xyz',
          external_url: null,
          cover_image_url: null,
          raw_attributes: {},
        },
      ],
      owned_matches: [],
      requires_manual_entry: false,
    }
    vi.mocked(barcodeApi.resolveBarcode).mockResolvedValue(result)
    vi.mocked(barcodeApi.createFromCandidate).mockResolvedValue({ id: 99 } as MediaItem)

    renderPage()
    const user = userEvent.setup()

    expect(await screen.findByText('Discovery')).toBeInTheDocument()
    expect(screen.getByText('Unrelated collided item')).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: /this is it/i })[0])

    await waitFor(() =>
      expect(barcodeApi.createFromCandidate).toHaveBeenCalledWith(
        expect.objectContaining({ barcode: '724384960650', media_type: 'CD' }),
      ),
    )
    expect(await screen.findByText('Item Detail')).toBeInTheDocument()
  })

  it('offers manual entry when nothing was found', async () => {
    vi.mocked(barcodeApi.resolveBarcode).mockResolvedValue({
      candidates: [],
      owned_matches: [],
      requires_manual_entry: true,
    })

    renderPage()

    expect(await screen.findByText(/nothing found/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /add manually/i })).toBeInTheDocument()
  })
})

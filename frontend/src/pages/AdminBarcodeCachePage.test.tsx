import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AdminBarcodeCachePage } from './AdminBarcodeCachePage'
import * as adminApi from '../api/admin'
import type { BarcodeCachePage } from '../types'

vi.mock('../api/admin')

const page: BarcodeCachePage = {
  items: [
    {
      barcode: '724384960650',
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
      last_refreshed_at: '2026-01-01T00:00:00Z',
      refresh_count: 3,
    },
  ],
  total: 1,
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminBarcodeCachePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminBarcodeCachePage', () => {
  it('lists cached barcodes with their candidate count and refresh count', async () => {
    vi.mocked(adminApi.listBarcodeCache).mockResolvedValue(page)

    renderPage()

    expect(await screen.findByText('724384960650')).toBeInTheDocument()
    expect(screen.getByText(/1 candidate/i)).toBeInTheDocument()
    expect(screen.getByText(/refreshed 3/i)).toBeInTheDocument()
  })

  it('purges a cache entry after confirmation', async () => {
    vi.mocked(adminApi.listBarcodeCache).mockResolvedValue(page)
    vi.mocked(adminApi.deleteBarcodeCache).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText('724384960650')
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /purge/i }))

    await waitFor(() => expect(adminApi.deleteBarcodeCache).toHaveBeenCalled())
    expect(vi.mocked(adminApi.deleteBarcodeCache).mock.calls[0][0]).toBe('724384960650')
  })

  it('shows an empty state when nothing is cached', async () => {
    vi.mocked(adminApi.listBarcodeCache).mockResolvedValue({ items: [], total: 0 })

    renderPage()

    expect(await screen.findByText(/no cached/i)).toBeInTheDocument()
  })
})

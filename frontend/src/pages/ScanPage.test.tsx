import { useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ScanPage } from './ScanPage'
import { useBarcodeScanner } from '../scanner/useBarcodeScanner'

vi.mock('../scanner/useBarcodeScanner')

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/scan']}>
      <Routes>
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/resolve/:barcode" element={<div>Resolution for barcode</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ScanPage', () => {
  it('navigates to the resolution page when the scanner decodes a barcode', async () => {
    vi.mocked(useBarcodeScanner).mockImplementation((_ref, onDecode) => {
      // Matches the real hook's timing: decode fires after render, via an effect, not during it.
      useEffect(() => {
        onDecode('724384960650')
      }, [onDecode])
    })

    renderPage()

    expect(await screen.findByText('Resolution for barcode')).toBeInTheDocument()
  })

  it('lets the member type a barcode manually and navigates on submit', async () => {
    vi.mocked(useBarcodeScanner).mockImplementation(() => {})
    renderPage()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText(/enter barcode manually/i), '9781593070209')
    await user.click(screen.getByRole('button', { name: /look up/i }))

    expect(await screen.findByText('Resolution for barcode')).toBeInTheDocument()
  })
})

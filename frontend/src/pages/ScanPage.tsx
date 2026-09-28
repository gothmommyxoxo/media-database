import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBarcodeScanner } from '../scanner/useBarcodeScanner'

export function ScanPage() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const navigate = useNavigate()
  const [manualBarcode, setManualBarcode] = useState('')
  const [decodedBarcode, setDecodedBarcode] = useState<string | null>(null)

  const handleDecode = useCallback((barcode: string) => {
    setDecodedBarcode((current) => current ?? barcode)
  }, [])

  useBarcodeScanner(videoRef, handleDecode, true)

  useEffect(() => {
    if (decodedBarcode) {
      navigate(`/resolve/${encodeURIComponent(decodedBarcode)}`)
    }
  }, [decodedBarcode, navigate])

  function handleManualSubmit(event: FormEvent) {
    event.preventDefault()
    if (!manualBarcode.trim()) return
    navigate(`/resolve/${encodeURIComponent(manualBarcode.trim())}`)
  }

  return (
    <div className="scan-page">
      <h1>Scan a barcode</h1>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video ref={videoRef} className="scanner-video" muted playsInline />

      <form onSubmit={handleManualSubmit} className="manual-barcode-form">
        <label htmlFor="manual-barcode">Or enter barcode manually</label>
        <input
          id="manual-barcode"
          value={manualBarcode}
          onChange={(e) => setManualBarcode(e.target.value)}
          inputMode="numeric"
        />
        <button type="submit">Look up</button>
      </form>
    </div>
  )
}

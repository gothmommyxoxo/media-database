import { useEffect, type RefObject } from 'react'
import { BrowserMultiFormatReader } from '@zxing/browser'

/** Section 5.1: decodes frames from the live camera stream client-side; only the decoded
 * barcode string is ever handed to the caller, no image data. */
export function useBarcodeScanner(
  videoRef: RefObject<HTMLVideoElement | null>,
  onDecode: (barcode: string) => void,
  enabled: boolean,
): void {
  useEffect(() => {
    if (!enabled) return

    const reader = new BrowserMultiFormatReader()
    let cancelled = false
    let controls: { stop: () => void } | undefined

    reader
      .decodeFromVideoDevice(undefined, videoRef.current ?? undefined, (result) => {
        if (result && !cancelled) {
          onDecode(result.getText())
        }
      })
      .then((c) => {
        controls = c
      })
      .catch(() => {
        // Camera unavailable or permission denied; ScanPage's manual-entry fallback covers this.
      })

    return () => {
      cancelled = true
      controls?.stop()
    }
  }, [videoRef, onDecode, enabled])
}

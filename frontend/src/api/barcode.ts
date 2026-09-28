import { apiFetch } from './client'
import type { BarcodeCandidate, MediaItem, MediaType, ResolutionResult } from '../types'

export function resolveBarcode(barcode: string): Promise<ResolutionResult> {
  return apiFetch<ResolutionResult>(`/barcode/${encodeURIComponent(barcode)}/resolve`)
}

export interface CreateFromCandidatePayload {
  candidate: BarcodeCandidate
  media_type: MediaType
  barcode: string
  overrides?: Record<string, unknown>
}

export function createFromCandidate(payload: CreateFromCandidatePayload): Promise<MediaItem> {
  return apiFetch<MediaItem>('/barcode/items', { method: 'POST', body: JSON.stringify(payload) })
}

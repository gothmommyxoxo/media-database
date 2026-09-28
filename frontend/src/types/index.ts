// Mirrors backend/app/models/enums.py (Section 3.1)
export type MediaType =
  | 'MANGA'
  | 'BOOK'
  | 'COMIC_BOOK'
  | 'GRAPHIC_NOVEL'
  | 'VIDEO_GAME'
  | 'BLU_RAY'
  | 'DVD'
  | 'VHS'
  | 'VCD'
  | 'LASERDISC'
  | 'CD'
  | 'VINYL'
  | 'CASSETTE'

export const MEDIA_TYPES: MediaType[] = [
  'MANGA',
  'BOOK',
  'COMIC_BOOK',
  'GRAPHIC_NOVEL',
  'VIDEO_GAME',
  'BLU_RAY',
  'DVD',
  'VHS',
  'VCD',
  'LASERDISC',
  'CD',
  'VINYL',
  'CASSETTE',
]

export type ItemSource = 'SCANNED' | 'MANUAL'

export type Role = 'ADMIN' | 'MEMBER'

export interface MediaItem {
  id: number
  media_type: MediaType
  title: string
  subtitle: string | null
  barcode: string | null
  format: string | null
  condition: string | null
  notes: string | null
  cover_image_url: string | null
  attributes: Record<string, unknown>
  external_ids: Record<string, string>
  source: ItemSource
  added_by: number | null
  created_at: string
  updated_at: string
}

export interface MediaItemPage {
  items: MediaItem[]
  total: number
}

export interface BarcodeCandidate {
  source_provider: string
  media_type: MediaType | null
  title: string
  subtitle: string | null
  external_id: string | null
  external_url: string | null
  cover_image_url: string | null
  raw_attributes: Record<string, unknown>
}

export interface ResolutionResult {
  candidates: BarcodeCandidate[]
  owned_matches: MediaItem[]
  requires_manual_entry: boolean
}

export interface User {
  id: number
  username: string
  display_name: string
  role: Role
  created_at: string
}

export interface BarcodeCacheEntry {
  barcode: string
  candidates: BarcodeCandidate[]
  last_refreshed_at: string
  refresh_count: number
}

export interface BarcodeCachePage {
  items: BarcodeCacheEntry[]
  total: number
}

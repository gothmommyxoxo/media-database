import { apiFetch } from './client'
import type { MediaItem, MediaItemPage, MediaType } from '../types'

export interface ListItemsParams {
  media_type?: MediaType[]
  search?: string
  added_by?: number
  sort?: 'title' | 'created_at' | 'updated_at'
}

function toQueryString(params: ListItemsParams): string {
  const query = new URLSearchParams()
  for (const type of params.media_type ?? []) query.append('media_type', type)
  if (params.search) query.set('search', params.search)
  if (params.added_by !== undefined) query.set('added_by', String(params.added_by))
  if (params.sort) query.set('sort', params.sort)
  const qs = query.toString()
  return qs ? `?${qs}` : ''
}

export function listItems(params: ListItemsParams = {}): Promise<MediaItemPage> {
  return apiFetch<MediaItemPage>(`/items${toQueryString(params)}`)
}

export function getItem(id: number): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/items/${id}`)
}

export interface CreateItemPayload {
  media_type: MediaType
  title: string
  subtitle?: string | null
  barcode?: string | null
  format?: string | null
  condition?: string | null
  notes?: string | null
  cover_image_url?: string | null
  attributes?: Record<string, unknown>
}

export function createItem(payload: CreateItemPayload): Promise<MediaItem> {
  return apiFetch<MediaItem>('/items', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateItem(id: number, payload: Partial<CreateItemPayload>): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deleteItem(id: number): Promise<void> {
  return apiFetch<void>(`/items/${id}`, { method: 'DELETE' })
}

import { apiFetch } from './client'
import type { BarcodeCacheEntry, BarcodeCachePage, MediaItem, Role, User } from '../types'

export interface CreateUserPayload {
  username: string
  display_name: string
  password: string
  role: Role
}

export interface UpdateUserPayload {
  username?: string
  display_name?: string
  role?: Role
}

export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>('/admin/users')
}

export function createUser(payload: CreateUserPayload): Promise<User> {
  return apiFetch<User>('/admin/users', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateUser(id: number, payload: UpdateUserPayload): Promise<User> {
  return apiFetch<User>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function resetPassword(id: number, newPassword: string): Promise<void> {
  return apiFetch<void>(`/admin/users/${id}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  })
}

export function deleteUser(id: number): Promise<void> {
  return apiFetch<void>(`/admin/users/${id}`, { method: 'DELETE' })
}

export interface AdminItemUpdatePayload {
  media_type?: string
  title?: string
  subtitle?: string | null
  barcode?: string | null
  format?: string | null
  condition?: string | null
  notes?: string | null
  cover_image_url?: string | null
  attributes?: Record<string, unknown>
  external_ids?: Record<string, string>
  source?: string
  added_by?: number | null
}

export function updateItemAdmin(id: number, payload: AdminItemUpdatePayload): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/admin/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function listBarcodeCache(page = 1): Promise<BarcodeCachePage> {
  return apiFetch<BarcodeCachePage>(`/admin/barcode-cache?page=${page}`)
}

export function getBarcodeCache(barcode: string): Promise<BarcodeCacheEntry> {
  return apiFetch<BarcodeCacheEntry>(`/admin/barcode-cache/${encodeURIComponent(barcode)}`)
}

export function deleteBarcodeCache(barcode: string): Promise<void> {
  return apiFetch<void>(`/admin/barcode-cache/${encodeURIComponent(barcode)}`, { method: 'DELETE' })
}

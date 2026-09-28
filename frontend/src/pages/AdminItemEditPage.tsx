import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { updateItemAdmin } from '../api/admin'
import { ApiError } from '../api/client'
import { getItem } from '../api/collection'
import { MEDIA_TYPES, type ItemSource, type MediaType } from '../types'

const emptyForm = {
  media_type: 'CD' as MediaType,
  title: '',
  subtitle: '',
  barcode: '',
  format: '',
  condition: '',
  notes: '',
  cover_image_url: '',
  source: 'MANUAL' as ItemSource,
  added_by: '',
  attributes: '{}',
  external_ids: '{}',
}

export function AdminItemEditPage() {
  const { id } = useParams<{ id: string }>()
  const itemId = Number(id)
  const navigate = useNavigate()
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)

  const { data: item } = useQuery({
    queryKey: ['items', itemId],
    queryFn: () => getItem(itemId),
  })

  useEffect(() => {
    if (item) {
      setForm({
        media_type: item.media_type,
        title: item.title,
        subtitle: item.subtitle ?? '',
        barcode: item.barcode ?? '',
        format: item.format ?? '',
        condition: item.condition ?? '',
        notes: item.notes ?? '',
        cover_image_url: item.cover_image_url ?? '',
        source: item.source,
        added_by: item.added_by === null ? '' : String(item.added_by),
        attributes: JSON.stringify(item.attributes, null, 2),
        external_ids: JSON.stringify(item.external_ids, null, 2),
      })
    }
  }, [item])

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    let attributes: Record<string, unknown>
    let externalIds: Record<string, string>
    try {
      attributes = JSON.parse(form.attributes)
      externalIds = JSON.parse(form.external_ids)
    } catch {
      setError('Attributes and External IDs must be valid JSON.')
      return
    }

    try {
      const updated = await updateItemAdmin(itemId, {
        media_type: form.media_type,
        title: form.title,
        subtitle: form.subtitle || null,
        barcode: form.barcode || null,
        format: form.format || null,
        condition: form.condition || null,
        notes: form.notes || null,
        cover_image_url: form.cover_image_url || null,
        source: form.source,
        added_by: form.added_by === '' ? null : Number(form.added_by),
        attributes,
        external_ids: externalIds,
      })
      navigate(`/items/${updated.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Save failed.')
    }
  }

  if (!item) return <p>Loading…</p>

  return (
    <div className="admin-item-edit-page">
      <h1>Admin edit: {item.title}</h1>
      <p>Every field on this record, including ones the normal edit form does not expose.</p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="media_type">Media type</label>
        <select id="media_type" value={form.media_type} onChange={(e) => update('media_type', e.target.value as MediaType)}>
          {MEDIA_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>

        <label htmlFor="title">Title</label>
        <input id="title" value={form.title} onChange={(e) => update('title', e.target.value)} required />

        <label htmlFor="subtitle">Subtitle</label>
        <input id="subtitle" value={form.subtitle} onChange={(e) => update('subtitle', e.target.value)} />

        <label htmlFor="barcode">Barcode</label>
        <input id="barcode" value={form.barcode} onChange={(e) => update('barcode', e.target.value)} />

        <label htmlFor="format">Format</label>
        <input id="format" value={form.format} onChange={(e) => update('format', e.target.value)} />

        <label htmlFor="condition">Condition</label>
        <input id="condition" value={form.condition} onChange={(e) => update('condition', e.target.value)} />

        <label htmlFor="notes">Notes</label>
        <textarea id="notes" value={form.notes} onChange={(e) => update('notes', e.target.value)} />

        <label htmlFor="cover_image_url">Cover image URL</label>
        <input
          id="cover_image_url"
          value={form.cover_image_url}
          onChange={(e) => update('cover_image_url', e.target.value)}
        />

        <label htmlFor="source">Source</label>
        <select id="source" value={form.source} onChange={(e) => update('source', e.target.value as ItemSource)}>
          <option value="MANUAL">MANUAL</option>
          <option value="SCANNED">SCANNED</option>
        </select>

        <label htmlFor="added_by">added_by (User id, blank = unassigned)</label>
        <input
          id="added_by"
          type="number"
          value={form.added_by}
          onChange={(e) => update('added_by', e.target.value)}
        />

        <label htmlFor="attributes">attributes (JSON)</label>
        <textarea id="attributes" value={form.attributes} onChange={(e) => update('attributes', e.target.value)} />

        <label htmlFor="external_ids">external_ids (JSON)</label>
        <textarea
          id="external_ids"
          value={form.external_ids}
          onChange={(e) => update('external_ids', e.target.value)}
        />

        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}

        <button type="submit">Save</button>
      </form>
    </div>
  )
}

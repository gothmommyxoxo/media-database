import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { createItem, getItem, updateItem, type CreateItemPayload } from '../api/collection'
import { MEDIA_TYPES, type MediaType } from '../types'

const emptyForm = {
  media_type: 'CD' as MediaType,
  title: '',
  subtitle: '',
  barcode: '',
  format: '',
  condition: '',
  notes: '',
}

export function ManualEntryPage() {
  const { id } = useParams<{ id: string }>()
  const isEditing = id !== undefined
  const itemId = isEditing ? Number(id) : undefined
  const navigate = useNavigate()

  const { data: existing } = useQuery({
    queryKey: ['items', itemId],
    queryFn: () => getItem(itemId!),
    enabled: isEditing,
  })

  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (existing) {
      setForm({
        media_type: existing.media_type,
        title: existing.title,
        subtitle: existing.subtitle ?? '',
        barcode: existing.barcode ?? '',
        format: existing.format ?? '',
        condition: existing.condition ?? '',
        notes: existing.notes ?? '',
      })
    }
  }, [existing])

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!form.title.trim()) {
      setError('Title is required.')
      return
    }

    const payload: CreateItemPayload = {
      media_type: form.media_type,
      title: form.title,
      subtitle: form.subtitle || null,
      barcode: form.barcode || null,
      format: form.format || null,
      condition: form.condition || null,
      notes: form.notes || null,
    }

    try {
      const item = isEditing && itemId ? await updateItem(itemId, payload) : await createItem(payload)
      navigate(`/items/${item.id}`)
    } catch {
      setError('Could not save this item. Please try again.')
    }
  }

  return (
    <div className="manual-entry-page">
      <h1>{isEditing ? 'Edit item' : 'Add item manually'}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="media_type">Media type</label>
        <select
          id="media_type"
          value={form.media_type}
          onChange={(e) => update('media_type', e.target.value as MediaType)}
          disabled={isEditing}
        >
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
        <input
          id="format"
          placeholder="e.g. Steelbook, Picture Disc"
          value={form.format}
          onChange={(e) => update('format', e.target.value)}
        />

        <label htmlFor="condition">Condition</label>
        <input id="condition" value={form.condition} onChange={(e) => update('condition', e.target.value)} />

        <label htmlFor="notes">Notes</label>
        <textarea id="notes" value={form.notes} onChange={(e) => update('notes', e.target.value)} />

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

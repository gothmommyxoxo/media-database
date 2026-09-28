import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listItems } from '../api/collection'
import { useAuth } from '../auth/AuthContext'
import { MEDIA_TYPES, type MediaType } from '../types'

export function CollectionPage() {
  const { isAdmin } = useAuth()
  const [search, setSearch] = useState('')
  const [mediaTypes, setMediaTypes] = useState<MediaType[]>([])
  const [sort, setSort] = useState<'title' | 'created_at' | 'updated_at'>('title')

  const { data, isLoading } = useQuery({
    queryKey: ['items', { search, mediaTypes, sort }],
    queryFn: () => listItems({ search: search || undefined, media_type: mediaTypes, sort }),
  })

  function toggleMediaType(type: MediaType) {
    setMediaTypes((current) =>
      current.includes(type) ? current.filter((t) => t !== type) : [...current, type],
    )
  }

  return (
    <div className="collection-page">
      <header className="collection-toolbar">
        <input
          type="search"
          placeholder="Search title, subtitle, notes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
          <option value="title">Title</option>
          <option value="created_at">Recently added</option>
          <option value="updated_at">Recently updated</option>
        </select>
        <Link to="/scan">Scan barcode</Link>
        <Link to="/items/new">Add manually</Link>
        {isAdmin && <Link to="/admin/users">Admin</Link>}
      </header>

      <div className="media-type-filters">
        {MEDIA_TYPES.map((type) => (
          <label key={type}>
            <input
              type="checkbox"
              checked={mediaTypes.includes(type)}
              onChange={() => toggleMediaType(type)}
            />
            {type}
          </label>
        ))}
      </div>

      {isLoading && <p>Loading…</p>}

      {!isLoading && data?.items.length === 0 && <p>No items in your collection yet.</p>}

      <ul className="item-grid">
        {data?.items.map((item) => (
          <li key={item.id}>
            <Link to={`/items/${item.id}`}>
              <span className="media-type-badge">{item.media_type}</span>
              <span>{item.title}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

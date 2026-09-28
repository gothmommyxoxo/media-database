import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteItem, getItem } from '../api/collection'
import { useAuth } from '../auth/AuthContext'

export function ItemDetailPage() {
  const { isAdmin } = useAuth()
  const { id } = useParams<{ id: string }>()
  const itemId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: item, isLoading } = useQuery({
    queryKey: ['items', itemId],
    queryFn: () => getItem(itemId),
  })

  async function handleDelete() {
    if (!window.confirm('Delete this item? This cannot be undone.')) return
    await deleteItem(itemId)
    await queryClient.invalidateQueries({ queryKey: ['items'] })
    navigate('/')
  }

  if (isLoading) return <p>Loading…</p>
  if (!item) return <p>Item not found.</p>

  return (
    <div className="item-detail-page">
      <span className="media-type-badge">{item.media_type}</span>
      <h1>{item.title}</h1>
      {item.subtitle && <h2>{item.subtitle}</h2>}
      {item.barcode && (
        <p>
          Barcode: <code>{item.barcode}</code>
        </p>
      )}
      {item.condition && <p>Condition: {item.condition}</p>}
      {item.notes && <p>Notes: {item.notes}</p>}

      <dl>
        {Object.entries(item.attributes).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>

      <Link to={`/items/${item.id}/edit`}>Edit</Link>
      {isAdmin && <Link to={`/admin/items/${item.id}`}>Admin edit</Link>}
      <button type="button" onClick={handleDelete}>
        Delete
      </button>
    </div>
  )
}

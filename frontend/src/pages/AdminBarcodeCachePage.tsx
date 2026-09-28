import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { deleteBarcodeCache, listBarcodeCache } from '../api/admin'

export function AdminBarcodeCachePage() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'barcode-cache'],
    queryFn: () => listBarcodeCache(),
  })

  async function handlePurge(barcode: string) {
    if (!window.confirm(`Purge the cached resolution for ${barcode}? The next scan will re-resolve from scratch.`))
      return
    await deleteBarcodeCache(barcode)
    await queryClient.invalidateQueries({ queryKey: ['admin', 'barcode-cache'] })
  }

  return (
    <div className="admin-barcode-cache-page">
      <p>
        <Link to="/">&larr; Back to collection</Link> · <Link to="/admin/users">Household accounts</Link>
      </p>
      <h1>Cached barcode resolutions</h1>

      {isLoading && <p>Loading…</p>}
      {!isLoading && data?.items.length === 0 && <p>No cached barcode resolutions.</p>}

      <ul>
        {data?.items.map((entry) => (
          <li key={entry.barcode}>
            <code>{entry.barcode}</code>
            <span>
              {entry.candidates.length} candidate{entry.candidates.length === 1 ? '' : 's'}
            </span>
            <span>refreshed {entry.refresh_count} time(s)</span>
            <span>last refreshed {new Date(entry.last_refreshed_at).toLocaleString()}</span>
            <button type="button" onClick={() => handlePurge(entry.barcode)}>
              Purge
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

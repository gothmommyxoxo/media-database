import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createFromCandidate, resolveBarcode } from '../api/barcode'
import { MEDIA_TYPES, type BarcodeCandidate, type MediaType } from '../types'

export function ResolutionPage() {
  const { barcode } = useParams<{ barcode: string }>()
  const navigate = useNavigate()
  const [selectedTypes, setSelectedTypes] = useState<Record<number, MediaType>>({})
  const [submitting, setSubmitting] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['resolve', barcode],
    queryFn: () => resolveBarcode(barcode!),
    enabled: !!barcode,
  })

  async function handleSelect(candidate: BarcodeCandidate, index: number) {
    const mediaType = candidate.media_type ?? selectedTypes[index]
    if (!mediaType || !barcode) return
    setSubmitting(true)
    try {
      const item = await createFromCandidate({ candidate, media_type: mediaType, barcode })
      navigate(`/items/${item.id}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) return <p>Loading…</p>
  if (!data) return null

  return (
    <div className="resolution-page">
      <h1>
        Barcode: <code>{barcode}</code>
      </h1>

      {data.owned_matches.length > 0 && (
        <section className="owned-matches">
          <h2>You already own this</h2>
          <ul>
            {data.owned_matches.map((item) => (
              <li key={item.id}>
                <Link to={`/items/${item.id}`}>{item.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.candidates.length > 0 && (
        <section className="candidates">
          <h2>Select the correct match</h2>
          <ul>
            {data.candidates.map((candidate, index) => (
              <li key={`${candidate.source_provider}-${candidate.external_id ?? index}`}>
                <span className="candidate-title">{candidate.title}</span>
                {candidate.subtitle && <span> — {candidate.subtitle}</span>}
                <span className="source-provider"> ({candidate.source_provider})</span>

                {!candidate.media_type && (
                  <select
                    aria-label={`Media type for ${candidate.title}`}
                    value={selectedTypes[index] ?? ''}
                    onChange={(e) =>
                      setSelectedTypes((current) => ({
                        ...current,
                        [index]: e.target.value as MediaType,
                      }))
                    }
                  >
                    <option value="">Choose type…</option>
                    {MEDIA_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                )}

                <button
                  type="button"
                  disabled={submitting || (!candidate.media_type && !selectedTypes[index])}
                  onClick={() => handleSelect(candidate, index)}
                >
                  This is it
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.requires_manual_entry && <p>Nothing found for this barcode.</p>}

      <Link to={`/items/new?barcode=${encodeURIComponent(barcode ?? '')}`}>Add manually</Link>
    </div>
  )
}

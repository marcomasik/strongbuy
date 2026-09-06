import { useEffect, useState } from 'react'

// Step 6: prove the chain DB -> FastAPI -> browser works.
// Deliberately unstyled. The real UI (filtering, sorting, styling) is step 7.

const COLUMNS = [
  'ticker',
  'company',
  'recommendation_key',
  'recommendation_mean',
  'num_analysts',
  'price',
  'target_mean_price',
  'upside_pct',
]

export default function App() {
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  // Load the category list once on mount.
  useEffect(() => {
    fetch('/api/categories')
      .then((r) => r.json())
      .then((body) => {
        setCategories(body.categories)
        if (body.categories.length > 0) setCategory(body.categories[0])
      })
      .catch((e) => setError(String(e)))
  }, [])

  // Load stocks whenever the selected category changes.
  useEffect(() => {
    if (!category) return
    setData(null)
    setError(null)
    fetch(`/api/stocks?category=${encodeURIComponent(category)}`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [category])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: 16 }}>
      <h1>strong_buy_screener</h1>

      <p>
        Category:{' '}
        <select
          value={category ?? ''}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </p>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {data && (
        <>
          <p>
            {data.count} tickers &middot; latest scan: {data.run_at ?? '(none)'}
          </p>
          <table border="1" cellPadding="4" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.stocks.map((row, i) => (
                <tr key={row.ticker ?? i}>
                  {COLUMNS.map((col) => (
                    <td key={col}>{row[col] ?? ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {!data && !error && <p>Loading…</p>}
    </div>
  )
}

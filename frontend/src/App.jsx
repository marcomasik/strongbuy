import { useEffect, useState } from 'react'

const COLUMNS = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'company', label: 'Company' },
  { key: 'recommendation_key', label: 'Rating' },
  { key: 'recommendation_mean', label: 'Rating (mean)' },
  { key: 'num_analysts', label: 'Analysts' },
  { key: 'price', label: 'Price' },
  { key: 'target_mean_price', label: 'Target' },
  { key: 'upside_pct', label: 'Upside %' },
]

function formatDate(isoString) {
  if (!isoString) return '—'
  return isoString.slice(0, 10)
}

function formatCell(key, value) {
  if (value === null || value === undefined) return '—'
  switch (key) {
    case 'price':
    case 'target_mean_price':
      return `$${Number(value).toFixed(2)}`
    case 'upside_pct':
      return `${Number(value).toFixed(1)}%`
    case 'recommendation_mean':
      return Number(value).toFixed(2)
    default:
      return value
  }
}

function fetchScans(category) {
  return fetch(`/api/scans?category=${encodeURIComponent(category)}`).then(
    (r) => r.json(),
  )
}

export default function App() {
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState(null)
  const [scans, setScans] = useState([])
  const [scanId, setScanId] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [scanStatus, setScanStatus] = useState(null)

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

  // Load the available scan dates whenever the category changes, and
  // default to the most recent one.
  useEffect(() => {
    if (!category) return
    setScans([])
    setScanId(null)
    fetchScans(category)
      .then((body) => {
        setScans(body.scans)
        if (body.scans.length > 0) setScanId(body.scans[0].id)
      })
      .catch((e) => setError(String(e)))
  }, [category])

  // Load the stock table whenever the category or selected scan changes.
  useEffect(() => {
    if (!category || scanId === null) return
    setData(null)
    setError(null)
    fetch(
      `/api/stocks?category=${encodeURIComponent(category)}&scan_id=${scanId}`,
    )
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [category, scanId])

  // While a scan is running, poll its status. When it finishes, refresh
  // the date list (and select the new scan) so the new data shows up.
  useEffect(() => {
    if (!scanStatus?.running) return
    const scanningCategory = scanStatus.category
    const interval = setInterval(() => {
      fetch('/api/scans/status')
        .then((r) => r.json())
        .then((status) => {
          setScanStatus(status)
          if (!status.running) {
            clearInterval(interval)
            if (!status.error && scanningCategory === category) {
              fetchScans(category).then((body) => {
                setScans(body.scans)
                if (body.scans.length > 0) setScanId(body.scans[0].id)
              })
            }
          }
        })
        .catch((e) => setError(String(e)))
    }, 3000)
    return () => clearInterval(interval)
  }, [scanStatus, category])

  function runScan() {
    if (!category) return
    setError(null)
    fetch(`/api/scans/run?category=${encodeURIComponent(category)}`, {
      method: 'POST',
    })
      .then(async (r) => {
        const body = await r.json()
        if (!r.ok) throw new Error(body.detail ?? 'Failed to start scan')
        setScanStatus(body)
      })
      .catch((e) => setError(String(e)))
  }

  return (
    <div className="screener">
      <div className="screener__crumbs">Strong Buy Screener</div>

      <div className="screener__controls">
        <label className="select-control">
          <span className="select-control__label">Category</span>
          <select
            className="select-control__input"
            value={category ?? ''}
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label className="select-control">
          <span className="select-control__label">Scan date</span>
          <select
            className="select-control__input"
            value={scanId ?? ''}
            onChange={(e) => setScanId(Number(e.target.value))}
            disabled={scans.length === 0}
          >
            {scans.map((s) => (
              <option key={s.id} value={s.id}>
                {formatDate(s.run_at)}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="scan-button"
          onClick={runScan}
          disabled={!category || scanStatus?.running}
        >
          {scanStatus?.running ? 'Scanning…' : 'Scan now'}
        </button>
      </div>

      {scanStatus?.running && (
        <p className="screener__meta">
          Scanning {scanStatus.category}… (started{' '}
          {scanStatus.started_at?.replace('T', ' ')})
        </p>
      )}
      {scanStatus && !scanStatus.running && scanStatus.error && (
        <p className="screener__error">
          Scan of {scanStatus.category} failed: {scanStatus.error}
        </p>
      )}

      {error && <p className="screener__error">Error: {error}</p>}

      {data && (
        <>
          <p className="screener__meta">
            {data.count} tickers &middot; scan: {formatDate(data.run_at)}
          </p>
          <div className="screener__table-wrap">
            <table className="stock-table">
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <th key={col.key} className="stock-table__head-cell">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.stocks.map((row, i) => (
                  <tr key={row.ticker ?? i} className="stock-table__row">
                    {COLUMNS.map((col) => (
                      <td key={col.key} className="stock-table__cell">
                        {formatCell(col.key, row[col.key])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!data && !error && <p className="screener__meta">Loading…</p>}
    </div>
  )
}

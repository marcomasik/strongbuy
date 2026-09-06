# frontend

Vite + React (JavaScript) UI for `strong_buy_screener`.

At this stage (plan step 6) it just proves the chain **SQLite -> FastAPI -> browser**:
it fetches `/api/categories`, lets you pick one, and dumps the latest scan's rows
into a plain table. Styling and real filtering/sorting come in step 7.

## Dev workflow (two terminals)

**Terminal 1 — API** (from the project root):

```
./.venv/bin/uvicorn api:app --reload
```

Serves on http://localhost:8000.

**Terminal 2 — frontend** (from this `frontend/` folder):

```
npm install   # first time only
npm run dev
```

Serves on http://localhost:5173. Vite proxies `/api/*` to the API server
(see `server.proxy` in `vite.config.js`), so the browser makes same-origin
requests and no CORS config is needed.

## Build

```
npm run build     # outputs to dist/
npm run preview    # serve the built dist/ locally
```

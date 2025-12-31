# Pastebin Lite

A lightweight "Pastebin"-like application for sharing text snippets with optional expiration and view limits. Built with **FastAPI** and **Upstash Redis** for production-ready serverless deployment.

**🚀 [Try Live Demo](https://pastebin-lite-lu55.onrender.com)**

## Features

✅ Create and share text pastes  
✅ Shareable URLs with unique IDs  
✅ TTL (Time-to-Live) expiry  
✅ View-count limits  
✅ Safe HTML rendering (no XSS)  
✅ Stateless, serverless-compatible design  
✅ Persistent storage across requests  

## Deployment Status

| Environment | Status | URL |
|-------------|--------|-----|
| **Production** | ✅ Live | https://pastebin-lite-lu55.onrender.com |
| **Repository** | ✅ Active | [GitHub](https://github.com/Zubin123/pastebin_lite) |
| **Database** | ✅ Connected | Upstash Redis |

## Quick Start

### Prerequisites
- Python 3.10+
- Redis (local or Upstash cloud)

### Installation

```bash
# Clone repo
git clone <your-repo-url>
cd pastebin_lite

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows or: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your REDIS_URL and APP_DOMAIN
```

### Running Locally

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` to create pastes.

## API Endpoints

### Health Check
```http
GET /api/healthz
```
Example: `curl https://pastebin-lite-lu55.onrender.com/api/healthz`

Response: `{"ok": true}`

### Create Paste
```http
POST /api/pastes
Content-Type: application/json

{
  "content": "Your text here",
  "ttl_seconds": 3600,      // Optional: expires after 1 hour
  "max_views": 5            // Optional: viewable max 5 times
}
```

Response (201):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "http://localhost:8000/p/550e8400-e29b-41d4-a716-446655440000"
}
```

### Fetch Paste (API)
```http
GET /api/pastes/:id
```

Response (200):
```json
{
  "content": "Your text here",
  "remaining_views": 4,
  "expires_at": "2026-01-01T12:00:00.000Z"
}
```

Returns 404 if paste is missing, expired, or view limit exceeded.

### View Paste (Web)
```http
GET /p/:id
```

Returns HTML page with paste content or 404 error page.

## Persistence Layer

**Upstash Redis** for persistent key-value storage.

### Why Redis?
- **Built-in TTL:** Auto-expires keys using `EXPIRE` command
- **Atomic Operations:** View counting via `INCR` prevents race conditions
- **Fast:** Sub-millisecond responses, ideal for serverless
- **Simple:** No schema migrations, no complex queries
- **Serverless-Ready:** Upstash provides managed Redis

### Data Model
```
Key: paste:{uuid}
Fields:
  - content: text content
  - created_at: ISO 8601 timestamp
  - ttl_seconds: optional TTL (stored as string)
  - max_views: optional view limit (stored as string)
  - views: current view count (incremented per fetch)
```

## Design Decisions

1. **Stateless Architecture:** No global mutable state. All data in Redis → horizontally scalable & serverless-compatible.

2. **UUID4 IDs:** Collision-resistant, URL-safe, no database sequences needed.

3. **Deterministic Testing:** Set `TEST_MODE=1` env var to use `x-test-now-ms` header for custom timestamps (bypasses real system time for testing).

4. **Atomic View Counting:** Redis `INCR` ensures thread-safe, race-condition-free counters.

5. **Safe Rendering:** Jinja2 auto-escaping prevents XSS. Pastes rendered as plain text.

6. **Dynamic URLs:** Generated from `request.base_url` + `APP_DOMAIN` env var (no hardcoded localhost).

7. **Error Handling:** 
   - Invalid input → 400 with JSON error
   - Unavailable pastes (expired/over-limit/missing) → 404 with JSON
   - Health check → 200 with `{"ok": true/false}`

## Deployment

### Deploy on Render.com

1. Sign up at https://render.com
2. Create Web Service, connect GitHub repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add Redis service (or use Upstash)
6. Set environment variables: `REDIS_URL`, `APP_DOMAIN`

### Using Upstash Redis

1. Sign up at https://upstash.com
2. Create free Redis database
3. Copy Redis connection string
4. Set in deployment: `REDIS_URL=rediss://default:{password}@{host}:{port}`

## File Structure

```
pastebin_lite/
├── app/
│   ├── main.py              # FastAPI app, routes
│   ├── config.py            # Environment configuration
│   ├── models.py            # Pydantic schemas
│   ├── database.py          # Redis connection & helpers
│   ├── routes/
│   │   ├── health.py        # GET /api/healthz
│   │   └── pastes.py        # Paste CRUD endpoints
│   └── templates/
│       ├── create.html      # Create paste form
│       └── view.html        # View paste page
├── static/                  # Static files (CSS/JS)
│   └── .gitkeep             # Placeholder for git tracking
├── .env                     # Environment variables (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

## Testing

### Manual API Test (curl)

```bash
# Create a paste
curl -X POST http://localhost:8000/api/pastes \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello", "ttl_seconds": 60, "max_views": 3}'

# Fetch paste
curl http://localhost:8000/api/pastes/{id}

# Test with custom timestamp (TEST_MODE=1 required)
curl -H "x-test-now-ms: 1704067200000" http://localhost:8000/api/pastes/{id}

# Health check
curl http://localhost:8000/api/healthz
```

## Troubleshooting

**Q: Pastes don't persist after restart?**  
A: Verify `.env` has correct `REDIS_URL`. Check Redis connection in logs.

**Q: `ConnectionError` on startup?**  
A: Ensure Redis is accessible. For local: start `redis-server`. For Upstash: check URL format is `rediss://` (double 's' for SSL).

**Q: TTL tests failing?**  
A: Set `TEST_MODE=1` and send `x-test-now-ms` header with milliseconds since epoch.

## Architecture Notes

- **Framework:** FastAPI (async, type-safe, auto-validation)
- **Server:** Uvicorn (production-ready ASGI)
- **Language:** Python 3.10.11
- **Deployment:** Serverless-compatible (stateless, no file I/O)
- **Database:** Upstash Redis (managed, no ops needed)

---

**Built for the Pastebin Lite Take-Home Assignment**



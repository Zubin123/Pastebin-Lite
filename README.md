# Pastebin Lite

A lightweight, fast "Pastebin"-like application for sharing text snippets with optional expiration and view limits. Built with Python FastAPI for serverless-ready deployment.

## Features

- **Create Pastes:** Share text content instantly
- **Shareable URLs:** Get a unique link to view your paste
- **Time-to-Live (TTL):** Pastes automatically expire after a set time
- **View Limits:** Restrict how many times a paste can be viewed
- **Deterministic Testing:** Support for test mode with controlled timestamps
- **Stateless Design:** Works perfectly in serverless environments

## Prerequisites

- **Python:** 3.10.11 or higher
- **Redis:** For persistent storage across requests
  - Local installation: Download from https://redis.io or via Chocolatey (`choco install redis-64` on Windows)
  - Or use Upstash Redis (free tier): https://upstash.com

## Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd pastebin_lite
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or: source venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env and set your REDIS_URL and APP_DOMAIN
```

**Example .env for local development:**
```
REDIS_URL=redis://localhost:6379
APP_DOMAIN=http://localhost:8000
DEBUG=True
TEST_MODE=0
```

### 5. Start Redis (if running locally)
```bash
# Windows with Chocolatey installed Redis
redis-server

# Or use WSL/Docker
# docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Run the Application
```bash
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`. Visit the UI at `http://localhost:8000/` to create pastes.

## API Endpoints

### Health Check
```
GET /api/healthz
```
Returns JSON indicating if the app and database are operational.

**Response:**
```json
{
  "ok": true
}
```

### Create Paste
```
POST /api/pastes
Content-Type: application/json

{
  "content": "Your text here",
  "ttl_seconds": 3600,        // Optional: expires in 1 hour
  "max_views": 5              // Optional: can be viewed max 5 times
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "http://localhost:8000/p/550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors (400):**
```json
{
  "detail": "content is required and must be non-empty"
}
```

### Fetch Paste (API)
```
GET /api/pastes/:id
```

**Response (200):**
```json
{
  "content": "Your text here",
  "remaining_views": 4,
  "expires_at": "2026-01-01T12:00:00.000Z"
}
```

**Unavailable (404):**
```json
{
  "detail": "Paste not found, expired, or view limit exceeded"
}
```

### View Paste (HTML)
```
GET /p/:id
```

Returns HTML page with paste content or 404 error page.

## Persistence Layer

### Why Redis?

This project uses **Redis** as the persistence layer for the following reasons:

1. **Key-Value Store:** Perfect for storing pastes as JSON blobs
2. **Built-in TTL:** Redis `EXPIRE` command automatically removes expired pastes
3. **Atomic Operations:** `INCR` command ensures view counts don't race in concurrent scenarios
4. **Fast:** Sub-millisecond response times, ideal for serverless
5. **Simple:** No schema migrations or complex queries needed
6. **Serverless-Friendly:** Upstash provides managed Redis for serverless deployments

### Data Structure

Each paste is stored as a Redis hash:

```
Key: paste:{id}
Fields:
  - content: Text content
  - ttl_seconds: Optional TTL in seconds
  - max_views: Optional max view count
  - views: Current view count (incremented per fetch)
  - created_at: Timestamp of creation (ISO 8601)
```

**Alternative:** PostgreSQL can be used instead (see below) for more complex queries.

## Design Decisions

### 1. **Stateless Architecture**
No global mutable state in Python. All data persists in Redis, making the app horizontally scalable and serverless-compatible.

### 2. **UUID4 for Paste IDs**
Collision-resistant, URL-safe, no sequence guessing, no database auto-increments needed.

### 3. **Deterministic Testing**
When `TEST_MODE=1`:
- The `x-test-now-ms` header (milliseconds since epoch) overrides system time for expiry logic
- Allows reproducible tests without waiting for real TTLs
- Useful for CI/CD pipelines and automated grading

### 4. **Atomic View Counting**
Uses Redis `INCR` command to avoid race conditions:
- Multiple simultaneous requests increment correctly
- No negative view counts possible
- Thread-safe and process-safe

### 5. **Safe HTML Rendering**
Jinja2's auto-escaping prevents XSS attacks. Paste content rendered as plain text, not HTML.

### 6. **Dynamic URL Generation**
No hardcoded localhost URLs. URLs are generated from `request.base_url` and `APP_DOMAIN` env var.

### 7. **Graceful Error Handling**
- Invalid input returns 400 with detailed error messages
- Unavailable pastes (expired, over-limit, missing) return 404
- Health check distinguishes app vs. database failures

### 8. **Minimal Dependencies**
Only essential packages to reduce attack surface and keep deployment size small.

## Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Manual API Testing (with curl)
```bash
# Create a paste
curl -X POST http://localhost:8000/api/pastes \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello World", "ttl_seconds": 60, "max_views": 3}'

# Fetch the paste
curl http://localhost:8000/api/pastes/{id}

# Test with deterministic time
curl -H "x-test-now-ms: 1704067200000" http://localhost:8000/api/pastes/{id}
```

## Deployment

### Deploy on Railway.app (Recommended)

1. **Sign up** at https://railway.app
2. **Connect** your GitHub repository
3. **Add Services:**
   - Click "Add Service" → "Provision Redis"
   - Railway auto-generates `REDIS_URL` environment variable
4. **Deploy:** Push to main branch; Railway auto-deploys
5. **Set Env Vars:**
   ```
   APP_DOMAIN=https://{your-railway-app}.railway.app
   DEBUG=False
   TEST_MODE=0
   ```

### Deploy on Render.com

1. **Sign up** at https://render.com
2. **Create Web Service** → Connect GitHub repo
3. **Settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Add PostgreSQL or Redis** (Render managed service)
5. **Environment Variables:** Set `REDIS_URL`, `APP_DOMAIN`

### Using Upstash Redis (Serverless)

1. **Sign up** at https://upstash.com
2. **Create Redis database** (free tier)
3. **Copy REST API URL** or Redis connection string
4. **Set in deployment:**
   ```
   REDIS_URL=redis://default:{password}@{host}:{port}
   ```

## Troubleshooting

### Redis Connection Error
**Problem:** `ConnectionError: Error 111 connecting to localhost:6379`
**Solution:** Ensure Redis is running. Start with `redis-server` or use Upstash Redis.

### Paste Not Persisting
**Problem:** Pastes disappear after restart or multiple requests
**Solution:** Verify `.env` has correct `REDIS_URL`. In-memory storage won't work.

### Time-based Tests Failing
**Problem:** TTL tests fail on expiry
**Solution:** Ensure `TEST_MODE=1` is set and `x-test-now-ms` header is sent with tests.

### CORS Issues
**Problem:** Frontend can't call API from different domain
**Solution:** Uncomment CORS middleware in `app/main.py` and configure allowed origins.

## File Structure

```
pastebin_lite/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Environment config
│   ├── models.py            # Pydantic schemas
│   ├── database.py          # Redis connection & helpers
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py        # /api/healthz
│   │   └── pastes.py        # Paste CRUD endpoints
│   └── templates/
│       ├── create.html      # Paste creation form
│       └── view.html        # Paste viewer
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_health.py
│   └── test_pastes.py
├── static/                  # CSS/JS (minimal)
├── .env.example             # Template for env vars
├── .gitignore
├── requirements.txt
└── README.md
```

## Performance & Limits

- **Paste Size:** No hard limit, but keep under 10MB for fast responses
- **Concurrent Users:** Scales horizontally with Uvicorn workers
- **Redis TTL Precision:** 1 second granularity
- **View Count:** Integer-based, no limit

## License

MIT

## Support

For issues, questions, or improvements, open an issue on GitHub or contact the maintainers.

---

**Happy Pasting! 🎉**

"""
Paste routes.
Handles create, fetch (API), and view (HTML) operations.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from app.models import PasteCreate, PasteResponse, PasteView
from app.database import db
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_current_time(x_test_now_ms: Optional[str] = None) -> datetime:
    """
    Get current time, respecting TEST_MODE for deterministic testing.
    
    Args:
        x_test_now_ms: Test timestamp header (milliseconds since epoch)
    
    Returns:
        Current datetime in UTC
    """
    if settings.TEST_MODE and x_test_now_ms:
        try:
            # Convert milliseconds to seconds
            timestamp_ms = int(x_test_now_ms)
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid x-test-now-ms header: {e}")

    return datetime.now(timezone.utc)


@router.post("/api/pastes", response_model=PasteResponse, status_code=201)
async def create_paste(
    paste: PasteCreate,
    request: Request,
) -> PasteResponse:
    """
    Create a new paste.

    Args:
        paste: Paste data (content, optional ttl_seconds, optional max_views)
        request: HTTP request context

    Returns:
        Paste ID and shareable URL

    Raises:
        HTTPException: If input is invalid
    """
    # Validate input
    if not paste.content or not paste.content.strip():
        raise HTTPException(
            status_code=400,
            detail="content is required and must be non-empty",
        )

    if paste.ttl_seconds is not None and paste.ttl_seconds < 1:
        raise HTTPException(
            status_code=400,
            detail="ttl_seconds must be >= 1",
        )

    if paste.max_views is not None and paste.max_views < 1:
        raise HTTPException(
            status_code=400,
            detail="max_views must be >= 1",
        )

    # Generate unique paste ID
    paste_id = str(uuid.uuid4())

    # Save to database
    success = db.save_paste(
        paste_id=paste_id,
        content=paste.content,
        ttl_seconds=paste.ttl_seconds,
        max_views=paste.max_views,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to save paste",
        )

    # Generate shareable URL
    base_url = settings.APP_DOMAIN.rstrip("/")
    url = f"{base_url}/p/{paste_id}"

    return PasteResponse(id=paste_id, url=url)


@router.get("/api/pastes/{paste_id}", response_model=PasteView)
async def fetch_paste(
    paste_id: str,
    request: Request,
    x_test_now_ms: Optional[str] = Header(None),
) -> PasteView:
    """
    Fetch a paste (API endpoint).
    Each fetch increments the view count.

    Args:
        paste_id: Unique paste identifier
        request: HTTP request context
        x_test_now_ms: Optional test timestamp (TEST_MODE only)

    Returns:
        Paste content with metadata

    Raises:
        HTTPException: If paste not found, expired, or view limit exceeded (404)
    """
    paste_data = db.get_paste(paste_id)

    if not paste_data:
        raise HTTPException(
            status_code=404,
            detail="Paste not found, expired, or view limit exceeded",
        )

    # Check TTL-based expiry with test time support
    if "ttl_seconds" in paste_data:
        created_at = datetime.fromisoformat(paste_data["created_at"])
        ttl_seconds = int(paste_data["ttl_seconds"])
        now = _get_current_time(x_test_now_ms)
        elapsed = (now - created_at).total_seconds()

        if elapsed > ttl_seconds:
            db.delete_paste(paste_id)
            raise HTTPException(
                status_code=404,
                detail="Paste not found, expired, or view limit exceeded",
            )

    # Calculate remaining views before incrementing
    remaining_views = None
    if "max_views" in paste_data:
        max_views = int(paste_data["max_views"])
        current_views = int(paste_data.get("views", 0))
        remaining_views = max_views - current_views
        
        # Check if already at limit
        if remaining_views <= 0:
            db.delete_paste(paste_id)
            raise HTTPException(
                status_code=404,
                detail="Paste not found, expired, or view limit exceeded",
            )

    # Increment view count
    db.increment_views(paste_id)
    
    # Recalculate remaining views after increment
    if remaining_views is not None:
        remaining_views -= 1

    # Calculate expires_at
    expires_at = None
    if "ttl_seconds" in paste_data:
        created_at = datetime.fromisoformat(paste_data["created_at"])
        ttl_seconds = int(paste_data["ttl_seconds"])
        expires_at = (created_at + timedelta(seconds=ttl_seconds)).isoformat() + "Z"

    return PasteView(
        content=paste_data["content"],
        remaining_views=remaining_views,
        expires_at=expires_at,
    )


@router.get("/p/{paste_id}", response_class=HTMLResponse)
async def view_paste(
    paste_id: str,
    request: Request,
    x_test_now_ms: Optional[str] = Header(None),
) -> str:
    """
    View a paste as HTML.
    Each view increments the view count.

    Args:
        paste_id: Unique paste identifier
        request: HTTP request context
        x_test_now_ms: Optional test timestamp (TEST_MODE only)

    Returns:
        HTML page with paste content, or 404 error page

    Raises:
        HTTPException: If paste not found, expired, or view limit exceeded (404)
    """
    paste_data = db.get_paste(paste_id)

    if not paste_data:
        return _render_404_page()

    # Check TTL-based expiry with test time support
    if "ttl_seconds" in paste_data:
        created_at = datetime.fromisoformat(paste_data["created_at"])
        ttl_seconds = int(paste_data["ttl_seconds"])
        now = _get_current_time(x_test_now_ms)
        elapsed = (now - created_at).total_seconds()

        if elapsed > ttl_seconds:
            db.delete_paste(paste_id)
            return _render_404_page()

    # Check view limit
    if "max_views" in paste_data:
        max_views = int(paste_data["max_views"])
        current_views = int(paste_data.get("views", 0))
        if current_views >= max_views:
            db.delete_paste(paste_id)
            return _render_404_page()

    # Increment view count
    db.increment_views(paste_id)

    # Render paste content safely (Jinja2 auto-escapes)
    content = paste_data["content"]
    # Escape HTML entities for safe display
    content_escaped = (
        content
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paste - Pastebin Lite</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            max-width: 900px;
            width: 100%;
            padding: 40px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }}
        .paste-id {{
            color: #666;
            font-size: 12px;
            margin-bottom: 30px;
            font-family: monospace;
            word-break: break-all;
        }}
        .content {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            font-family: "Courier New", monospace;
            font-size: 14px;
            line-height: 1.6;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #333;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Pastebin Lite</h1>
        <div class="paste-id">ID: {paste_id}</div>
        <div class="content">{content_escaped}</div>
        <div class="footer">
            <p><a href="/">Create a new paste</a></p>
        </div>
    </div>
</body>
</html>"""


def _render_404_page() -> str:
    """Render a 404 error page."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Not Found - Pastebin Lite</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
            padding: 60px 40px;
            text-align: center;
        }}
        h1 {{
            font-size: 48px;
            color: #667eea;
            margin-bottom: 20px;
        }}
        p {{
            color: #666;
            font-size: 16px;
            margin-bottom: 30px;
            line-height: 1.6;
        }}
        a {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 600;
            transition: background 0.3s;
        }}
        a:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>404</h1>
        <p>
            Oops! This paste was not found, has expired, or its view limit has been exceeded.
        </p>
        <a href="/">Create a new paste</a>
    </div>
</body>
</html>"""

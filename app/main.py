"""
Pastebin Lite - Main FastAPI application.
"""
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, pastes
from app.database import db  # Initialize database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pastebin Lite",
    description="A lightweight Pastebin-like application for sharing text",
    version="1.0.0",
)

# Add CORS middleware (optional, for cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include route modules
app.include_router(health.router)
app.include_router(pastes.router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Pastebin Lite application starting...")
    
    # Log database status
    if db.using_fallback:
        logger.warning("⚠️  DATABASE: Using IN-MEMORY storage (Redis not available)")
        logger.warning("   Data will NOT persist across server restarts!")
    else:
        logger.info("✅ DATABASE: Connected to Upstash Redis")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Pastebin Lite application shutting down...")


@app.get("/", response_class=FileResponse)
async def root():
    """Serve the create paste HTML page."""
    return FileResponse("app/templates/create.html", media_type="text/html")


@app.get("/api/docs", include_in_schema=False)
async def docs():
    """OpenAPI documentation."""
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

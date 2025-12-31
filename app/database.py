"""
Database layer for Redis operations with in-memory fallback for development.
Handles paste CRUD, expiry, view counting, and health checks.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from redis import Redis
from redis.exceptions import ConnectionError

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryStore:
    """Simple in-memory store for development/testing (when Redis unavailable)."""

    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}
        self.ttl_timestamps: Dict[str, float] = {}

    def hset(self, key: str, mapping: Dict[str, Any]):
        """Store hash data."""
        self.store[key] = mapping

    def hgetall(self, key: str) -> Dict[str, Any]:
        """Retrieve hash data."""
        if key not in self.store:
            return {}
        
        # Check if expired
        if key in self.ttl_timestamps:
            now = datetime.now(timezone.utc).timestamp() * 1000
            if now > self.ttl_timestamps[key]:
                del self.store[key]
                del self.ttl_timestamps[key]
                return {}
        
        return self.store[key]

    def expire(self, key: str, seconds: int):
        """Set expiry time in seconds."""
        expire_time = (datetime.now(timezone.utc).timestamp() + seconds) * 1000
        self.ttl_timestamps[key] = expire_time

    def hincrby(self, key: str, field: str, increment: int):
        """Increment hash field."""
        if key not in self.store:
            self.store[key] = {}
        current = int(self.store[key].get(field, 0))
        self.store[key][field] = current + increment

    def delete(self, key: str):
        """Delete a key."""
        self.store.pop(key, None)
        self.ttl_timestamps.pop(key, None)

    def ping(self):
        """Health check."""
        return True


class PasteDatabase:
    """Wrapper for Redis operations on pastes."""

    def __init__(self):
        """Initialize Redis connection, fallback to in-memory store."""
        self.using_fallback = False
        try:
            # For Upstash Redis, use rediss:// scheme for SSL/TLS
            logger.info(f"Attempting to connect to Redis: {settings.REDIS_URL[:30]}...")
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            # Test connection
            self.redis.ping()
            logger.info("✓ Redis connected successfully to Upstash")
        except ConnectionError as e:
            logger.error(f"❌ ConnectionError connecting to Redis: {type(e).__name__}: {str(e)}")
            logger.warning("Using in-memory fallback for development. Data will NOT persist across restarts.")
            self.redis = InMemoryStore()
            self.using_fallback = True
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Redis: {type(e).__name__}: {str(e)}")
            logger.warning("Using in-memory fallback for development. Data will NOT persist across restarts.")
            self.redis = InMemoryStore()
            self.using_fallback = True

    def is_healthy(self) -> bool:
        """Check if database connection is alive."""
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        return False

    def save_paste(
        self,
        paste_id: str,
        content: str,
        ttl_seconds: Optional[int] = None,
        max_views: Optional[int] = None,
    ) -> bool:
        """
        Save a paste to database.

        Args:
            paste_id: Unique paste identifier
            content: Text content of the paste
            ttl_seconds: Optional time-to-live in seconds
            max_views: Optional maximum view count

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"paste:{paste_id}"
            now = self._get_current_time()

            paste_data = {
                "content": content,
                "created_at": now.isoformat(),
                "views": 0,
            }

            if ttl_seconds is not None:
                paste_data["ttl_seconds"] = str(ttl_seconds)

            if max_views is not None:
                paste_data["max_views"] = str(max_views)

            # Store paste as hash
            self.redis.hset(key, mapping=paste_data)

            # Set expiry if TTL specified
            if ttl_seconds:
                self.redis.expire(key, ttl_seconds)

            logger.info(f"Paste {paste_id} saved successfully")
            return True

        except Exception as e:
            logger.error(f"Error saving paste {paste_id}: {e}")
            return False

    def get_paste(self, paste_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a paste from database.

        Args:
            paste_id: Unique paste identifier

        Returns:
            Paste data dict or None if not found/unavailable
        """
        try:
            key = f"paste:{paste_id}"
            paste_data = self.redis.hgetall(key)

            if not paste_data:
                logger.warning(f"Paste {paste_id} not found")
                return None

            # Check if paste has expired (TTL enforced by Redis)
            # Redis automatically deletes expired keys, so if we got here, it's not expired by TTL

            # Check view limit
            if "max_views" in paste_data:
                max_views = int(paste_data["max_views"])
                current_views = int(paste_data.get("views", 0))
                if current_views >= max_views:
                    logger.warning(f"Paste {paste_id} view limit exceeded")
                    return None

            # Check TTL-based expiry (manual check in case Redis TTL didn't trigger)
            if "ttl_seconds" in paste_data:
                created_at = datetime.fromisoformat(paste_data["created_at"])
                ttl_seconds = int(paste_data["ttl_seconds"])
                now = self._get_current_time()
                elapsed = (now - created_at).total_seconds()

                if elapsed > ttl_seconds:
                    logger.warning(f"Paste {paste_id} has expired (TTL)")
                    # Clean up
                    self.redis.delete(key)
                    return None

            return paste_data

        except Exception as e:
            logger.error(f"Error fetching paste {paste_id}: {e}")
            return None

    def increment_views(self, paste_id: str) -> bool:
        """
        Increment view count for a paste (atomic operation).

        Args:
            paste_id: Unique paste identifier

        Returns:
            True if increment successful, False otherwise
        """
        try:
            key = f"paste:{paste_id}"
            # INCR is atomic, prevents race conditions
            self.redis.hincrby(key, "views", 1)
            logger.info(f"View count incremented for paste {paste_id}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing views for {paste_id}: {e}")
            return False

    def delete_paste(self, paste_id: str) -> bool:
        """
        Delete a paste from database.

        Args:
            paste_id: Unique paste identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"paste:{paste_id}"
            self.redis.delete(key)
            logger.info(f"Paste {paste_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting paste {paste_id}: {e}")
            return False

    def _get_current_time(self) -> datetime:
        """
        Get current time, respecting TEST_MODE for deterministic testing.

        Returns:
            Current datetime in UTC
        """
        return datetime.now(timezone.utc)


# Global database instance
db = PasteDatabase()

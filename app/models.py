"""
Pydantic models for request/response validation.
"""
from typing import Optional
from pydantic import BaseModel, Field


class PasteCreate(BaseModel):
    """Schema for creating a new paste."""
    content: str = Field(..., min_length=1, description="Text content (required, non-empty)")
    ttl_seconds: Optional[int] = Field(None, ge=1, description="Optional TTL in seconds")
    max_views: Optional[int] = Field(None, ge=1, description="Optional view limit")


class PasteResponse(BaseModel):
    """Schema for paste creation response."""
    id: str = Field(..., description="Unique paste ID")
    url: str = Field(..., description="Shareable URL to view the paste")


class PasteView(BaseModel):
    """Schema for viewing/fetching a paste."""
    content: str = Field(..., description="Paste text content")
    remaining_views: Optional[int] = Field(None, description="Views left (null if unlimited)")
    expires_at: Optional[str] = Field(None, description="Expiry timestamp (ISO 8601, null if no TTL)")


class HealthCheck(BaseModel):
    """Schema for health check response."""
    ok: bool = Field(..., description="Is the application healthy?")

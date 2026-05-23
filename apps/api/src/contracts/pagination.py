"""
Pagination contracts for cursor-based and offset-based pagination.

All list endpoints use PaginationParams as input and return
PaginatedResponse to provide consistent traversal semantics.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""

    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Envelope for paginated responses.

    next_cursor enables cursor-based continuation for
    realtime-compatible clients that need resumption semantics.
    """

    items: List[T]
    total: int
    offset: int
    limit: int
    next_cursor: Optional[str] = None

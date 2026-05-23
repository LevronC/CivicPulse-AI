"""
API key authentication dependency.

This is a baseline auth mechanism for protecting mutating endpoints.
It will be replaced by JWT-based auth in the production hardening phase,
but the interface (FastAPI dependency) remains the same.
"""

from fastapi import Header, HTTPException

from src.config import get_settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = get_settings().api.api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

"""
ALAS — Laravel API client
Thin HTTP wrapper used by all auth/license/reports services.
Reads ALAS_API_BASE_URL from .env (default: http://localhost:8000).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from app.logger import get_logger

logger = get_logger("auth.api_client")

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_BASE_URL = os.getenv("ALAS_API_BASE_URL", "http://localhost:8000").rstrip("/")
_TIMEOUT = float(os.getenv("ALAS_API_TIMEOUT", "15"))


class ApiError(Exception):
    """Raised on transport / decode failure. HTTP error responses are returned, not raised."""


def _url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"{_BASE_URL}/api{path}"


def _headers(token: Optional[str] = None, json: bool = True) -> dict:
    h = {"Accept": "application/json"}
    if json:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[dict] = None,
    files: Optional[dict] = None,
    data: Optional[dict] = None,
    stream: bool = False,
) -> requests.Response:
    """
    Perform an HTTP request against the Laravel API.
    Returns the raw Response so callers can inspect status_code and JSON.
    """
    url = _url(path)
    try:
        if files is not None:
            resp = requests.request(
                method, url,
                headers=_headers(token, json=False),
                data=data, files=files, timeout=_TIMEOUT, stream=stream,
            )
        else:
            resp = requests.request(
                method, url,
                headers=_headers(token, json=True),
                json=json_body, timeout=_TIMEOUT, stream=stream,
            )
        return resp
    except requests.RequestException as e:
        logger.error(f"API request failed {method} {path}: {e}")
        raise ApiError(str(e)) from e


def base_url() -> str:
    return _BASE_URL

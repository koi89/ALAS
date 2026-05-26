"""
ALAS — License Service
Talks to the Laravel desktop API for license verification + activation.
"""

from __future__ import annotations

import datetime
import hashlib
import platform
import sys
import uuid
from dataclasses import dataclass
from typing import Optional

from app.auth.api_client import ApiError, request
from app.logger import get_logger

logger = get_logger("auth.license")

APP_VERSION = "1.0.0"


@dataclass
class LicenseStatus:
    key: str
    status: str
    max_devices: int
    expires_at: Optional[datetime.datetime]


def get_machine_id() -> str:
    """Stable per-device identifier (sha256 of MAC+hostname+platform)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def verify_license(token: str, machine_id: str) -> Optional[LicenseStatus]:
    """Return the user's usable license for this device, or None."""
    if not token:
        return None
    try:
        resp = request("POST", "/license/status", token=token,
                       json_body={"machine_id": machine_id})
    except ApiError:
        return None
    if not resp.ok:
        return None
    body = resp.json()
    if not body.get("licensed"):
        return None
    return _from_payload(body)


def activate_license(token: str, license_key: str, machine_id: str) -> LicenseStatus | str:
    """Activate `license_key` for the current user on this machine."""
    key = license_key.strip().upper()
    if not key:
        return "license.error_empty_key"

    try:
        resp = request("POST", "/license/activate-current", token=token, json_body={
            "license_key": key,
            "machine_id":  machine_id,
            "hostname":    platform.node(),
            "platform":    _platform(),
            "app_version": APP_VERSION,
        })
    except ApiError:
        return "license.error_processing_failed"

    if resp.ok:
        return _from_payload(resp.json())

    body = _safe_json(resp)
    err = body.get("error") if isinstance(body, dict) else None
    mapping = {
        "invalid_key":          "license.error_invalid_key",
        "not_owner":            "license.error_not_owner",
        "inactive_or_expired":  "license.error_inactive",
        "device_limit":         "license.error_device_limit",
    }
    return mapping.get(err, "license.error_processing_failed")


# ---------------------------------------------------------------------------

def _from_payload(p: dict) -> LicenseStatus:
    return LicenseStatus(
        key=p.get("key", ""),
        status=p.get("status", ""),
        max_devices=int(p.get("max_devices") or 0),
        expires_at=_parse_dt(p.get("expires_at")),
    )


def _parse_dt(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_json(resp) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {}

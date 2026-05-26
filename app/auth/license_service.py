"""
ALAS — License Service
Queries the Laravel-owned `licenses` and `license_activations` tables on NeonDB
to gate the desktop app behind a valid, activated license.
"""

from __future__ import annotations

import hashlib
import platform
import sys
import uuid
from dataclasses import dataclass
from typing import Optional

from app.auth.db import get_connection
from app.logger import get_logger

logger = get_logger("auth.license")

APP_VERSION = "1.0.0"


@dataclass
class LicenseStatus:
    key: str
    status: str
    max_devices: int
    expires_at: object  # datetime or None


def get_machine_id() -> str:
    """Stable per-device identifier (sha256 of mac+node+platform)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def verify_license(user_id: int, machine_id: str) -> Optional[LicenseStatus]:
    """
    Return the user's usable, activated license for this device, or None.
    Refreshes last_seen_at on success.
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT l.id, l.key, l.status, l.max_devices, l.expires_at
                    FROM licenses l
                    JOIN license_activations a ON a.license_id = l.id
                    WHERE l.user_id = %s
                      AND l.status = 'active'
                      AND (l.expires_at IS NULL OR l.expires_at > NOW())
                      AND a.machine_id = %s
                      AND a.deactivated_at IS NULL
                    ORDER BY l.created_at DESC
                    LIMIT 1
                    """,
                    (user_id, machine_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                lic_id, key, status, max_devices, expires_at = row
                cur.execute(
                    """
                    UPDATE license_activations
                    SET last_seen_at = NOW(), updated_at = NOW(),
                        app_version = %s
                    WHERE license_id = %s AND machine_id = %s
                    """,
                    (APP_VERSION, lic_id, machine_id),
                )
        conn.close()
        return LicenseStatus(key, status, max_devices, expires_at)
    except Exception as e:
        logger.warning(f"verify_license error: {e}")
        return None


def activate_license(user_id: int, license_key: str, machine_id: str) -> LicenseStatus | str:
    """
    Activate `license_key` on this machine for `user_id`.
    Returns LicenseStatus on success, error string code on failure.
    """
    key = license_key.strip().upper()
    if not key:
        return "license.error_empty_key"

    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, status, max_devices, expires_at, key
                    FROM licenses
                    WHERE key = %s
                    """,
                    (key,),
                )
                row = cur.fetchone()
                if not row:
                    return "license.error_invalid_key"

                lic_id, owner_id, status, max_devices, expires_at, db_key = row

                if owner_id != user_id:
                    return "license.error_not_owner"
                if status != "active":
                    return "license.error_inactive"
                if expires_at is not None:
                    cur.execute("SELECT NOW() > %s", (expires_at,))
                    if cur.fetchone()[0]:
                        return "license.error_expired"

                cur.execute(
                    """
                    SELECT id, deactivated_at FROM license_activations
                    WHERE license_id = %s AND machine_id = %s
                    """,
                    (lic_id, machine_id),
                )
                existing = cur.fetchone()

                if existing:
                    cur.execute(
                        """
                        UPDATE license_activations
                        SET deactivated_at = NULL,
                            hostname = %s, platform = %s, app_version = %s,
                            last_seen_at = NOW(), updated_at = NOW()
                        WHERE id = %s
                        """,
                        (platform.node(), get_platform(), APP_VERSION, existing[0]),
                    )
                else:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM license_activations
                        WHERE license_id = %s AND deactivated_at IS NULL
                        """,
                        (lic_id,),
                    )
                    active_count = cur.fetchone()[0]
                    if active_count >= max_devices:
                        return "license.error_device_limit"

                    cur.execute(
                        """
                        INSERT INTO license_activations
                            (license_id, machine_id, hostname, platform, app_version,
                             last_seen_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                        """,
                        (lic_id, machine_id, platform.node(), get_platform(), APP_VERSION),
                    )
        conn.close()
        logger.info(f"License {key} activated for user {user_id}")
        return LicenseStatus(db_key, status, max_devices, expires_at)
    except Exception as e:
        logger.error(f"activate_license error: {e}")
        return "license.error_processing_failed"

"""
ALAS — Auth Service
Talks to the Laravel desktop API for register/login/session/subscription.
No direct DB access.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Optional

from app.auth.api_client import ApiError, request
from app.logger import get_logger

logger = get_logger("auth.service")


@dataclass
class User:
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    created_at: Optional[datetime.datetime]


@dataclass
class Subscription:
    plan_name: str
    billing_period: str  # monthly | annual | lifetime
    status: str          # trialing | active | past_due | canceled | lifetime | expired
    current_period_end: Optional[datetime.datetime]
    trial_ends_at: Optional[datetime.datetime]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register(full_name: str, email: str, phone: str, password: str) -> User | str:
    """Create a new user via Laravel API. Returns User on success, error code on failure."""
    if not _valid_email(email):
        return "auth.error_invalid_email"

    try:
        resp = request("POST", "/auth/register", json_body={
            "full_name": full_name.strip(),
            "email":     email.strip().lower(),
            "phone":     phone.strip() or None,
            "password":  password,
        })
    except ApiError:
        return "auth.error_processing_failed"

    if resp.status_code == 422:
        body = _safe_json(resp)
        errs = body.get("errors", {}) if isinstance(body, dict) else {}
        if "email" in errs:
            return "auth.error_email_taken"
        return "auth.error_invalid_email"
    if not resp.ok:
        logger.error(f"register failed [{resp.status_code}]: {resp.text[:200]}")
        return "auth.error_processing_failed"

    return _user_from_payload(resp.json().get("user", {}))


def login(email: str, password: str, remember_me: bool = False) -> tuple[User, str | None] | str:
    """Verify credentials via Laravel API. Returns (User, token_or_None) or error code."""
    try:
        resp = request("POST", "/auth/login", json_body={
            "email":       email.strip().lower(),
            "password":    password,
            "remember_me": bool(remember_me),
        })
    except ApiError:
        return "auth.error_processing_failed"

    if resp.status_code in (401, 422):
        return "auth.error_invalid_credentials"
    if not resp.ok:
        logger.error(f"login failed [{resp.status_code}]: {resp.text[:200]}")
        return "auth.error_processing_failed"

    body = resp.json()
    user = _user_from_payload(body.get("user", {}))
    token = body.get("token")
    return user, token


def verify_session(token: str) -> Optional[User]:
    """Return User if token is valid, else None."""
    if not token:
        return None
    try:
        resp = request("GET", "/auth/me", token=token)
    except ApiError:
        return None
    if not resp.ok:
        return None
    return _user_from_payload(resp.json().get("user", {}))


def get_subscription(token: str) -> Optional[Subscription]:
    """Return current user's subscription, or None."""
    if not token:
        return None
    try:
        resp = request("GET", "/auth/subscription", token=token)
    except ApiError:
        return None
    if not resp.ok:
        return None
    s = resp.json().get("subscription")
    if not s:
        return None
    return Subscription(
        plan_name=s["plan_name"],
        billing_period=s["billing_period"],
        status=s["status"],
        current_period_end=_parse_dt(s.get("current_period_end")),
        trial_ends_at=_parse_dt(s.get("trial_ends_at")),
    )


def logout(token: str):
    if not token:
        return
    try:
        request("POST", "/auth/logout", token=token)
    except ApiError as e:
        logger.warning(f"logout: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_from_payload(p: dict) -> User:
    return User(
        id=int(p["id"]),
        full_name=p.get("full_name") or p.get("name") or "",
        email=p.get("email", ""),
        phone=p.get("phone"),
        created_at=_parse_dt(p.get("created_at")),
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


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


# Backwards-compat alias: old call sites pass user_id; new API uses token.
# Kept here so any stray import keeps working — prefer get_subscription(token).
def get_subscription_by_id(_user_id: int) -> None:  # pragma: no cover
    return None

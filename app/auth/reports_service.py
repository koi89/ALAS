"""
ALAS — Analysis Reports Service
Talks to the Laravel desktop API for listing, uploading, sharing, and deleting
PDF analysis reports. PDF bytes are uploaded via multipart — no shared
filesystem access required.
"""

from __future__ import annotations

import datetime
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.auth.api_client import ApiError, request
from app.logger import get_logger

logger = get_logger("auth.reports_service")


@dataclass
class AnalysisReport:
    id: int
    user_id: int
    title: str
    filename: str
    size_bytes: int
    share_token: Optional[str]
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]

    def is_shared(self) -> bool:
        return self.share_token is not None

    @property
    def size_human(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 ** 2:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / (1024 ** 2):.1f} MB"

    @property
    def date_str(self) -> str:
        if not self.created_at:
            return "—"
        local_dt = self.created_at.astimezone(datetime.timezone.utc).astimezone()
        return local_dt.strftime("%d/%m/%Y %H:%M")


def upload_report(
    token: str,
    title: str,
    pdf_path: str | Path,
    filename: Optional[str] = None,
) -> AnalysisReport | str:
    """Upload a PDF + metadata to the Laravel API."""
    p = Path(pdf_path)
    if not p.exists():
        return "reports.error_save_failed"
    name = filename or p.name

    try:
        with open(p, "rb") as fh:
            resp = request(
                "POST", "/reports", token=token,
                files={"pdf": (name, fh, "application/pdf")},
                data={"title": title.strip()},
            )
    except (OSError, ApiError) as e:
        logger.error(f"upload_report error: {e}")
        return "reports.error_save_failed"

    if not resp.ok:
        logger.error(f"upload_report failed [{resp.status_code}]: {resp.text[:200]}")
        return "reports.error_save_failed"

    return _from_payload(resp.json().get("report", {}))


def get_user_reports(token: str) -> List[AnalysisReport]:
    """Return all reports for the current user."""
    if not token:
        return []
    try:
        resp = request("GET", "/reports", token=token)
    except ApiError as e:
        logger.error(f"get_user_reports error: {e}")
        return []
    if not resp.ok:
        return []
    return [_from_payload(r) for r in resp.json().get("reports", [])]


def delete_report(token: str, report_id: int) -> bool:
    """Delete a report (and its file) via API."""
    try:
        resp = request("DELETE", f"/reports/{report_id}", token=token)
    except ApiError:
        return False
    return resp.ok


def toggle_share(token: str, report_id: int) -> Optional[str]:
    """Toggle the share token. Returns the new token if now shared, else None."""
    try:
        resp = request("POST", f"/reports/{report_id}/share", token=token)
    except ApiError:
        return None
    if not resp.ok:
        return None
    body = resp.json()
    return body.get("token") if body.get("shared") else None


def download_report(token: str, report: AnalysisReport, dest_path: Optional[Path] = None) -> Optional[Path]:
    """Download a report's PDF bytes to dest_path (or a temp file). Returns the local path."""
    try:
        resp = request("GET", f"/reports/{report.id}/download", token=token, stream=True)
    except ApiError as e:
        logger.error(f"download_report error: {e}")
        return None
    if not resp.ok:
        return None

    if dest_path is None:
        fd, tmp = tempfile.mkstemp(suffix=".pdf", prefix=f"alas_report_{report.id}_")
        os.close(fd)
        dest_path = Path(tmp)

    try:
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    fh.write(chunk)
    except OSError as e:
        logger.error(f"download_report write error: {e}")
        return None
    return dest_path


# ---------------------------------------------------------------------------

def _from_payload(p: dict) -> AnalysisReport:
    return AnalysisReport(
        id=int(p["id"]),
        user_id=int(p["user_id"]),
        title=p.get("title", ""),
        filename=p.get("filename", ""),
        size_bytes=int(p.get("size_bytes") or 0),
        share_token=p.get("share_token"),
        created_at=_parse_dt(p.get("created_at")),
        updated_at=_parse_dt(p.get("updated_at")),
    )


def _parse_dt(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None

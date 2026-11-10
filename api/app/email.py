"""Email sending — async, dev-mode friendly.

Two modes:
  - **Dev mode** (default): `SMTP_HOST` is empty/unset → the email is logged
    to stdout instead of sent. Lets you run the backend locally with no SMTP
    server, and lets tests assert that "an email would have been sent".
  - **SMTP mode**: `SMTP_HOST` is set → use `aiosmtplib` to send via SMTP with
    STARTTLS (or plain, depending on `SMTP_USE_TLS`).

Dev-mode email capture:
  - If `EMAIL_LOG_FILE` is also set (and SMTP_HOST is empty), every email is
    appended to that file as a JSON line:
      {"to": "...", "subject": "...", "body": "...", "html": "...", "ts": ...}
    Lets test scripts capture real reset tokens / verification codes without
    SMTP — the same `send_email()` code path runs, just with a file sink.
    Leave `EMAIL_LOG_FILE` empty to disable (emails go to stdout only).

Public API:
  - `async def send_email(to, subject, body, html=None) -> None`

This module never raises — email failures are logged but do not propagate,
because password-reset requests must always return 200 (per the contract)
and we don't want an SMTP outage to break the auth flow. If you need strict
delivery guarantees, wrap calls in your own retry logic.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import get_settings

logger = logging.getLogger("app.email")
settings = get_settings()


def _is_dev_mode() -> bool:
    """True when SMTP_HOST is empty — dev mode (log instead of send)."""
    return not (settings.smtp_host or "").strip()


def _append_to_log_file(to: str, subject: str, body: str, html: str | None) -> None:
    """Append the email to EMAIL_LOG_FILE as a JSON line (if set).

    Idempotent — if the path is empty, returns silently. Uses append mode so
    multiple worker processes can write concurrently without clobbering each
    other (each write is a single line, atomic on POSIX for small sizes).
    """
    path = (settings.email_log_file or "").strip()
    if not path:
        return
    entry = {
        "to": to,
        "subject": subject,
        "body": body,
        "html": html,
        "ts": time.time(),
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        # Don't break the calling flow over a log-file write failure
        logger.warning("could not append to EMAIL_LOG_FILE %s: %s", path, e)


async def send_email(
    to: str,
    subject: str,
    body: str,
    html: str | None = None,
) -> None:
    """Send an email, or log it in dev mode.

    Always returns None — never raises. SMTP errors are logged as warnings
    so they don't break the calling flow (e.g. password-reset request must
    always return 200 to prevent email enumeration).

    In dev mode (SMTP_HOST empty), the email is printed to stdout AND,
    if EMAIL_LOG_FILE is set, appended there as a JSON line. The log file
    is what test scripts read to capture reset tokens / verification codes
    without needing a real SMTP server.

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: Plain-text body.
        html: Optional HTML body. If provided, sent as an alternative part.
    """
    if _is_dev_mode():
        # ── Dev mode: log the email so tests / developers can see it ──
        logger.info(
            "[dev-email] to=%s subject=%s\n%s",
            to,
            subject,
            body,
        )
        print(f"\n--- DEV EMAIL ---\nTo: {to}\nSubject: {subject}\n\n{body}\n---")
        # Also append to EMAIL_LOG_FILE if configured
        _append_to_log_file(to, subject, body, html)
        return

    # ── SMTP mode: send via aiosmtplib ────────────────────────────
    try:
        import aiosmtplib  # imported lazily so dev mode doesn't require it

        from email.message import EmailMessage

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if html:
            message.add_alternative(html, subtype="html")

        kwargs: dict[str, Any] = {
            "hostname": settings.smtp_host,
            "port": settings.smtp_port,
            "timeout": 30,
        }
        if settings.smtp_username and settings.smtp_password:
            kwargs["username"] = settings.smtp_username
            kwargs["password"] = settings.smtp_password
        if settings.smtp_use_tls:
            kwargs["start_tls"] = True

        await aiosmtplib.send(message, **kwargs)  # type: ignore[arg-type]
        logger.info("sent email to=%s subject=%s", to, subject)
    except Exception as e:  # noqa: BLE001 — we explicitly swallow email errors
        # Don't let SMTP failures break the calling flow. The caller
        # (e.g. password-reset request) handles user response independently.
        logger.warning("failed to send email to %s: %s", to, e)

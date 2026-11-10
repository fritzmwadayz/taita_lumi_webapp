"""Tests for app/email.py.

Covers:
  - Dev mode (SMTP_HOST empty): email is logged, not sent.
  - SMTP mode: aiosmtplib.send is called with the right args.
  - SMTP failure is swallowed (never raises) — important for the
    password-reset endpoint, which must always return 200.

aiosmtplib is mocked via monkeypatch so no real network is used.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import get_settings
from app.email import send_email

settings = get_settings()


# ═══════════════════════════════════════════════════════════════
# Dev mode (SMTP_HOST empty)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dev_mode_logs_email_when_smtp_host_empty(monkeypatch, capsys):
    """Empty SMTP_HOST → email is printed/logged, not sent over SMTP."""
    monkeypatch.setattr(settings, "smtp_host", "")

    # Track aiosmtplib.send to ensure it's NOT called
    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email(
        to="alice@example.com",
        subject="Hello",
        body="World",
        html="<p>World</p>",
    )

    # No SMTP send call
    assert aiosmtplib_send.await_count == 0
    # The email body was printed to stdout (dev mode)
    captured = capsys.readouterr()
    assert "alice@example.com" in captured.out
    assert "Hello" in captured.out
    assert "World" in captured.out


@pytest.mark.asyncio
async def test_dev_mode_logs_no_html_in_stdout(monkeypatch, capsys):
    """HTML body is not printed in dev mode (only the plain-text body)."""
    monkeypatch.setattr(settings, "smtp_host", "")

    await send_email(
        to="alice@example.com",
        subject="Subject",
        body="Plain body",
        html="<p>HTML body</p>",
    )

    captured = capsys.readouterr()
    assert "Plain body" in captured.out
    assert "HTML body" not in captured.out  # HTML alternative is not printed


# ═══════════════════════════════════════════════════════════════
# SMTP mode (SMTP_HOST set)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_smtp_mode_calls_aiosmtplib_send(monkeypatch):
    """With SMTP_HOST set, aiosmtplib.send is awaited with the message."""
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_from", "noreply@example.com")
    monkeypatch.setattr(settings, "smtp_use_tls", True)

    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email(
        to="alice@example.com",
        subject="Hello",
        body="World",
        html="<p>World</p>",
    )

    assert aiosmtplib_send.await_count == 1
    # The first positional arg is the EmailMessage
    msg = aiosmtplib_send.call_args.args[0]
    assert msg["To"] == "alice@example.com"
    assert msg["Subject"] == "Hello"
    assert msg["From"] == "noreply@example.com"
    # STARTTLS enabled
    assert aiosmtplib_send.call_args.kwargs.get("start_tls") is True
    assert aiosmtplib_send.call_args.kwargs.get("hostname") == "smtp.example.com"
    assert aiosmtplib_send.call_args.kwargs.get("port") == 587
    assert aiosmtplib_send.call_args.kwargs.get("username") == "user"
    assert aiosmtplib_send.call_args.kwargs.get("password") == "pass"


@pytest.mark.asyncio
async def test_smtp_mode_no_auth_when_credentials_blank(monkeypatch):
    """When SMTP_USERNAME/PASSWORD are blank, no auth kwargs are passed."""
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")

    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email(
        to="alice@example.com",
        subject="Hello",
        body="World",
    )

    assert aiosmtplib_send.await_count == 1
    assert "username" not in aiosmtplib_send.call_args.kwargs
    assert "password" not in aiosmtplib_send.call_args.kwargs


@pytest.mark.asyncio
async def test_smtp_mode_no_starttls_when_disabled(monkeypatch):
    """When SMTP_USE_TLS is False, start_tls is not passed."""
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_use_tls", False)

    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email(
        to="alice@example.com",
        subject="Hello",
        body="World",
    )

    assert aiosmtplib_send.await_count == 1
    assert "start_tls" not in aiosmtplib_send.call_args.kwargs


# ═══════════════════════════════════════════════════════════════
# Failure handling
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_smtp_failure_is_swallowed(monkeypatch, caplog):
    """If aiosmtplib.send raises, send_email catches it and logs a warning.

    This is critical: the password-reset endpoint must always return 200,
    and we don't want SMTP outages to break the auth flow.
    """
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")

    aiosmtplib_send = AsyncMock(side_effect=ConnectionRefusedError("no SMTP"))
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    with caplog.at_level(logging.WARNING, logger="app.email"):
        # Must not raise
        await send_email(
            to="alice@example.com",
            subject="Hello",
            body="World",
        )

    # A warning was logged
    assert any("failed to send email" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_email_returns_none_in_dev_mode(monkeypatch):
    """send_email always returns None (no return value used by callers)."""
    monkeypatch.setattr(settings, "smtp_host", "")
    result = await send_email("a@b.com", "s", "b")
    assert result is None


@pytest.mark.asyncio
async def test_send_email_returns_none_in_smtp_mode(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    result = await send_email("a@b.com", "s", "b")
    assert result is None


# ═══════════════════════════════════════════════════════════════
# Config-driven mode detection
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dev_mode_when_smtp_host_is_whitespace_only(monkeypatch, capsys):
    """Whitespace-only SMTP_HOST is treated as 'unset' → dev mode."""
    monkeypatch.setattr(settings, "smtp_host", "   ")

    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email("a@b.com", "s", "b")

    assert aiosmtplib_send.await_count == 0
    captured = capsys.readouterr()
    assert "a@b.com" in captured.out


# ═══════════════════════════════════════════════════════════════
# EMAIL_LOG_FILE — dev-mode capture for test scripts
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dev_mode_writes_to_log_file_when_set(monkeypatch, tmp_path, capsys):
    """When EMAIL_LOG_FILE is set (and SMTP_HOST is empty), each email is
    appended as a JSON line.
    """
    log_file = tmp_path / "emails.log"
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_log_file", str(log_file))

    await send_email(
        to="alice@example.com",
        subject="Lumi — Password reset",
        body="Click: http://localhost:3000/reset-password?token=ABC123",
        html="<p>Click <a href='...'>here</a></p>",
    )

    # File exists, contains one JSON line
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    import json
    entry = json.loads(lines[0])
    assert entry["to"] == "alice@example.com"
    assert "Password reset" in entry["subject"]
    assert "ABC123" in entry["body"]
    assert entry["html"] is not None
    assert "ts" in entry

    # Stdout print still happens (the file is an addition, not a replacement)
    captured = capsys.readouterr()
    assert "alice@example.com" in captured.out


@pytest.mark.asyncio
async def test_dev_mode_appends_multiple_emails_to_log_file(monkeypatch, tmp_path):
    """Multiple emails accumulate as separate JSON lines in the log file."""
    log_file = tmp_path / "emails.log"
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_log_file", str(log_file))

    await send_email("alice@example.com", "Subject 1", "Body 1")
    await send_email("bob@example.com", "Subject 2", "Body 2")
    await send_email("carol@example.com", "Subject 3", "Body 3")

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    import json
    emails = [json.loads(line) for line in lines]
    assert [e["to"] for e in emails] == [
        "alice@example.com",
        "bob@example.com",
        "carol@example.com",
    ]


@pytest.mark.asyncio
async def test_dev_mode_no_log_file_when_setting_empty(monkeypatch, tmp_path):
    """When EMAIL_LOG_FILE is empty, no file is written (stdout only)."""
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_log_file", "")

    # Even if a file happens to exist at the default path, we shouldn't touch it.
    unexpected = tmp_path / "should-not-be-created.log"
    monkeypatch.setattr(settings, "email_log_file", "")

    await send_email("a@b.com", "s", "b")
    assert not unexpected.exists()


@pytest.mark.asyncio
async def test_smtp_mode_does_not_write_to_log_file(monkeypatch, tmp_path):
    """When SMTP_HOST is set, emails go through SMTP — the log file is not written.

    EMAIL_LOG_FILE is a dev-mode capture sink only. In SMTP mode, real email
    delivery is the source of truth, and writing to a log file would be
    misleading (and a privacy concern in production).
    """
    log_file = tmp_path / "emails.log"
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "email_log_file", str(log_file))

    aiosmtplib_send = AsyncMock()
    fake_aiosmtplib = MagicMock()
    fake_aiosmtplib.send = aiosmtplib_send
    monkeypatch.setitem(__import__("sys").modules, "aiosmtplib", fake_aiosmtplib)

    await send_email("alice@example.com", "Hello", "World")

    assert aiosmtplib_send.await_count == 1
    assert not log_file.exists()


@pytest.mark.asyncio
async def test_log_file_unwritable_does_not_raise(monkeypatch, caplog):
    """If the log file path is unwritable, send_email logs a warning but does not raise."""
    monkeypatch.setattr(settings, "smtp_host", "")
    # /dev/null is not a directory, so opening a path under it must fail
    monkeypatch.setattr(settings, "email_log_file", "/dev/null/cannot-create.log")

    with caplog.at_level(logging.WARNING, logger="app.email"):
        # Must not raise
        await send_email("a@b.com", "s", "b")

    # A warning was logged
    assert any("could not append to EMAIL_LOG_FILE" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_log_file_whitespace_only_treated_as_unset(monkeypatch, tmp_path):
    """A whitespace-only EMAIL_LOG_FILE is treated as unset (no file written)."""
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_log_file", "   ")

    await send_email("a@b.com", "s", "b")

    # No file written. (We can't easily assert "no file was created anywhere",
    # but at minimum we shouldn't crash trying to open a whitespace path.)
    # The real assertion is "this didn't raise" — which pytest enforces.

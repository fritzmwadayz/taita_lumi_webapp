# Email

The backend sends only one kind of email today: the password-reset link.
But the email infrastructure is general — `app/email.py` exposes
`send_email(to, subject, body, html=None)` that any route can call.

Two modes:

- **Dev mode** (default, `SMTP_HOST` empty): emails are logged to stdout
  AND (if `EMAIL_LOG_FILE` is set) appended to a file as JSON lines. No
  real email is sent.
- **SMTP mode** (`SMTP_HOST` set): emails are sent via `aiosmtplib` with
  STARTTLS. Failures are logged but **never raised** — the calling flow
  (e.g. password-reset request) must always succeed to prevent email
  enumeration.

## Dev mode

When `SMTP_HOST` is empty (the default), every email goes to two places:

1. **stdout** — printed as a formatted block:
   ```
   --- DEV EMAIL ---
   To: alice@example.com
   Subject: Lumi — Password reset

   You requested a password reset for your Lumi dictionary account.
   ...
   ---
   ```

2. **`EMAIL_LOG_FILE`** (if set) — appended as a JSON line:
   ```json
   {"to":"alice@example.com","subject":"Lumi — Password reset","body":"You requested...","html":"<p>...</p>","ts":1731345218.04}
   ```

The JSON-line format is what the test scripts (`test_api_endpoints.sh`,
`test_full_api.sh`) read to capture real password-reset tokens without
SMTP. See [testing.md](testing.md#key-feature-real-reset-tokens-via-email_log_file).

### Why both?

- stdout: for humans looking at the terminal — instant feedback that
  "yes, an email would have been sent"
- log file: for test scripts — machine-readable, parseable with
  `python3 -c "import json; ..."`

### Why is the log file skipped in SMTP mode?

Because in SMTP mode, the real email delivery is the source of truth.
Writing to a log file in prod would be misleading (the email was
actually sent, not just logged) and a privacy concern (production
password-reset tokens sitting in a file).

## SMTP mode

When `SMTP_HOST` is set, `send_email()` builds an `EmailMessage` and
sends it via `aiosmtplib.send()` with these options:

```python
{
    "hostname": settings.smtp_host,
    "port": settings.smtp_port,
    "timeout": 30,
    # If SMTP_USERNAME and SMTP_PASSWORD are both set:
    "username": settings.smtp_username,
    "password": settings.smtp_password,
    # If SMTP_USE_TLS is true (default):
    "start_tls": True,
}
```

### Failure handling

SMTP errors are caught, logged as warnings (`logger.warning("failed to
send email to %s: %s", to, e)`), and **swallowed** — the calling flow
continues. This is intentional: the password-reset endpoint must always
return 200 (to prevent email enumeration), and we don't want an SMTP
outage to break the auth flow.

If you need strict delivery guarantees, wrap calls in your own retry
logic — the backend's `send_email()` is fire-and-forget.

## Provider setup

### Gmail (free, easy to test)

Gmail requires an **App Password** (regular passwords don't work since
2022 — "less secure apps" was removed).

1. Enable 2-Step Verification on your Google Account
   (`https://myaccount.google.com/security`)
2. Go to `https://myaccount.google.com/apppasswords`
3. Generate an app password for "Mail" — you get a 16-char string
4. Set env vars:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=you@gmail.com
   SMTP_PASSWORD=<16-char-app-password>
   SMTP_FROM=you@gmail.com
   SMTP_USE_TLS=true
   ```

**Caveats:**
- Free Gmail has a 500-email/day limit (and per-day/per-second rate limits)
- The "from" address must be your Gmail address (or an alias you've
  configured in Gmail Settings → Accounts → Send mail as)
- Not suitable for production volume — use a real provider

### SendGrid (production-grade, generous free tier)

1. Sign up at `https://sendgrid.com` (free tier: 100 emails/day forever)
2. Verify your sender domain (DNS records: SPF, DKIM, DMARC)
3. Create an API key: Settings → API Keys → Create API Key
   - Permissions: Restricted → Mail Send → Full Access
4. Set env vars:
   ```bash
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey                # literal string "apikey"
   SMTP_PASSWORD=<your-sendgrid-api-key>
   SMTP_FROM=noreply@your-domain.com
   SMTP_USE_TLS=true
   ```

**Caveats:**
- The sender address (`SMTP_FROM`) must be on a domain you've verified
- Free tier: 100 emails/day. Paid: 50k+/month.
- Better deliverability than Gmail for transactional email

### Resend (modern, developer-friendly)

1. Sign up at `https://resend.com` (free tier: 3,000 emails/month, 100/day)
2. Verify your domain (DNS records)
3. Get your API key: Dashboard → API Keys → Create
4. Set env vars:
   ```bash
   SMTP_HOST=smtp.resend.com
   SMTP_PORT=587
   SMTP_USERNAME=resend                # literal string "resend"
   SMTP_PASSWORD=<your-resend-api-key>
   SMTP_FROM=noreply@your-domain.com
   SMTP_USE_TLS=true
   ```

**Caveats:**
- Can also send via their HTTP API (faster, no SMTP handshake) — but
  the backend uses SMTP for simplicity. If you want HTTP, you'd need to
  add a `ResendProvider` class to `app/email.py`.
- For testing without a verified domain, you can send from
  `onboarding@resend.dev` to your own email only.

### Mailgun

1. Sign up at `https://mailgun.com`
2. Add and verify your domain (DNS)
3. Create an SMTP credential: Recipients → Domains → your-domain → SMTP
4. Set env vars:
   ```bash
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USERNAME=postmaster@your-domain.com
   SMTP_PASSWORD=<mailgun-smtp-password>
   SMTP_FROM=noreply@your-domain.com
   SMTP_USE_TLS=true
   ```

## Production checklist

Before going live with real email:

- [ ] SPF record: `v=spf1 include:<provider-spf> ~all` on your domain
- [ ] DKIM: provider gives you a TXT record to add
- [ ] DMARC: `v=DMARC1; p=quarantine; rua=mailto:...` (start with `p=none`, tighten later)
- [ ] `SMTP_FROM` on a domain you control (not `gmail.com` or `localhost`)
- [ ] `SMTP_FROM` is a verified sender on your provider
- [ ] Rate limits understood (most providers cap at 5-10 emails/sec)
- [ ] Bounce handling: set up a webhook to mark bounced emails as
      undeliverable (the backend doesn't do this yet — TODO)
- [ ] `EMAIL_LOG_FILE` empty in prod (so test tokens don't leak)
- [ ] `FRONTEND_URL` points at the real frontend (so reset links work)
- [ ] End-to-end test: register a real email you control, request a
      reset, click the link, set a new password, log in

## Testing the reset flow without SMTP

This is the recommended dev workflow — no SMTP provider needed, real
end-to-end flow.

### 1. Start the backend with dev_server.sh

```bash
./dev_server.sh --local
```

This sets:
- `SMTP_HOST=""` (dev mode)
- `EMAIL_LOG_FILE=/tmp/lumi-test-emails.log`
- `JWT_SECRET=test-secret-for-dev-only`
- `FRONTEND_URL=http://localhost:3000`

### 2. Request a reset

```bash
# First, register a user (so they have a password_hash)
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"AlicePass12345!"}' \
  http://localhost:8000/api/auth/register

# Then request the reset
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com"}' \
  http://localhost:8000/api/auth/password-reset/request
# {"status":"ok","message":"If an account exists for that email, a reset link has been sent."}
```

### 3. Read the token from the log file

```bash
# Pretty-print the latest reset email
tail -1 /tmp/lumi-test-emails.log | python3 -c "
import json, sys
e = json.loads(sys.stdin.read())
print(e['subject'])
print()
print(e['body'])
"
```

You'll see something like:

```
Lumi — Password reset

You requested a password reset for your Lumi dictionary account.

Click this link to set a new password:
http://localhost:3000/reset-password?token=eyJhbGciOiJIUzI1NiIs...

This link expires in 1 hour. If you didn't request this, you can safely ignore this email.

— The Lumi team
```

Copy the token from the URL.

### 4. Confirm the reset

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"token":"<paste-token-here>","new_password":"BrandNew12345!"}' \
  http://localhost:8000/api/auth/password-reset/confirm
# {"status":"ok","message":"Your password has been reset. Please log in."}
```

### 5. Login with the new password

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"BrandNew12345!"}' \
  http://localhost:8000/api/auth/login
# {"access_token":"...","refresh_token":"...","token_type":"bearer","expires_in":1800}
```

### Or: just run the test script

The test scripts do all of this for you. With the backend running:

```bash
./test_api_endpoints.sh   # 22 steps including the reset flow
./test_full_api.sh         # 79 steps, full lifecycle
```

The test script reads the token from the log file automatically — no
manual copy-paste needed.

## Troubleshooting

### Emails aren't being sent (SMTP mode)

Check the backend logs for warnings:
```
WARNING:app.email:failed to send email to alice@example.com: <error message>
```

Common causes:
- Wrong port (try 587 with TLS, or 465 without TLS for SMTPS)
- Wrong credentials (use App Password for Gmail, not your regular password)
- Sender not verified (the `SMTP_FROM` address must be on a verified
  domain for SendGrid/Resend/Mailgun)
- Firewall blocking outbound SMTP (some networks block port 25/465/587)

### Emails go to spam

- Check SPF/DKIM/DMARC DNS records
- Use a verified sender domain (not `gmail.com` for transactional volume)
- Avoid spammy words in the subject ("FREE", "CLICK HERE", all caps)
- The reset email subject is "Lumi — Password reset" — should be fine
- Check your provider's deliverability dashboard

### The test script can't find the token

The log file isn't being written. Make sure:
- The backend was started with `dev_server.sh --local` (which sets
  `EMAIL_LOG_FILE`), OR
- You set `EMAIL_LOG_FILE=/tmp/lumi-test-emails.log` manually before
  starting `uvicorn`
- `SMTP_HOST` is empty (or the log file is skipped in SMTP mode)

### `EMAIL_LOG_FILE` exists but is empty

You haven't sent any emails yet. Each request to
`/api/auth/password-reset/request` for a known, non-blocked,
password-having user appends one line.

### The token in the log file is expired

Tokens expire after 1 hour. Request a fresh one.

## See also

- [configuration.md](configuration.md) — every SMTP env var with defaults
- [authentication.md](authentication.md) — the password-reset flow itself
- [testing.md](testing.md) — how the test scripts read the log file
- [`app/email.py`](../app/email.py) — the implementation (short, ~150 lines)

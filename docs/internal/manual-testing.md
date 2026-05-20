# Manual Testing Guide

This guide walks through the full CLI surface. Run these after any significant change to verify that commands, flows, and output modes work end-to-end.

## Prerequisites

```bash
uv pip install -e ".[dev]"
uv run authsome --version
```

> **Note on reset:** `rm -rf ~/.authsome` clears local state but does **not** stop a running daemon. If you reset while the daemon is running, `daemon stop` will say "No managed daemon record was found" and leave the process alive. Kill it manually first: `kill $(lsof -ti :7998)`, then reset.

---

## 1. Initialization

```bash
# Kill daemon and start fresh (optional — skip to keep existing config)
kill $(lsof -ti :7998) 2>/dev/null; rm -rf ~/.authsome

uv run authsome whoami
```

**Expected:** Home directory, registered non-default identity handle, principal ID, vault ID, DID, encryption mode, daemon URL, and connected provider count (0).

```bash
uv run authsome whoami --json
```

**Expected:** Same data as structured JSON. Key fields: `home_directory`, `profile`, `principal_id`, `vault_id`, `did`, `registration_status`, `daemon_url`, `encryption_backend`, `connected_providers_count`.

```bash
uv run authsome doctor
```

**Expected:** Exit code `0`; `OK` printed for `spec_version`, `identity`, `providers`, `connections`, `vault`, `integrity`. A `Warnings:` block may appear (e.g. "no active provider connections found") — that is normal on a fresh install.

```bash
uv run authsome doctor --json
```

**Expected:** `{"status": "ready", "checks": {"spec_version": "ok", ...}, "issues": [], "warnings": [...]}`. The `warnings` array is non-empty on a fresh install with no connections.

---

## 2. Login — API Key

Uses Resend (or any `api_key` provider):

```bash
uv run authsome login resend
```

**Expected:**
- Terminal prints a session URL: `Visit: http://127.0.0.1:7998/auth/sessions/<id>/input`
- Browser opens a secure local bridge page served by the daemon — credentials are submitted directly to the local daemon, never to a third-party server
- Terminal immediately returns: "Login process started. The connection will be updated automatically once complete."
- Run `authsome list` to confirm completion

```bash
uv run authsome list
```

**Expected:** `resend` listed with status `connected`.

---

## 3. Login — OAuth2 PKCE

```bash
uv run authsome login github
```

**Expected:**
- Terminal prints a session URL: `Visit: http://127.0.0.1:7998/auth/sessions/<id>/input`
- Browser opens a secure local bridge page served by the daemon; the page initiates the OAuth redirect to `https://github.com/login/oauth/authorize?...` and captures the callback — credentials never leave localhost
- Terminal immediately returns: "Login process started. The connection will be updated automatically once complete."
- Run `authsome list` to confirm completion

```bash
uv run authsome list
```

**Expected:** `github` listed with status `connected`.

---

## 4. Login — Device Code (headless)

```bash
uv run authsome login github --flow device_code
```

**Expected:**
- Terminal prints a session URL: `Visit: http://127.0.0.1:7998/auth/sessions/<id>/input`
- Browser opens a secure local bridge page — leave Client ID blank to use GitHub's public device code flow; the device code URL and user code are shown in the browser
- Terminal immediately returns: "Login process started."
- Run `authsome list` to confirm completion

---

## 5. List

```bash
uv run authsome list
```

**Expected:** Table of all providers with columns `Provider`, `Source`, `Auth`, `Connection`, `Status`, `Expires`. Connected ones show connection name and status. Header line shows total and connected counts.

```bash
uv run authsome list --json
```

**Expected:** JSON with `bundled` and `custom` arrays; each connected provider has a non-empty `connections` array.

---

## 6. Get

```bash
uv run authsome get github
```

**Expected:** Connection metadata; sensitive fields show `***REDACTED***`.

```bash
uv run authsome get github --show-secret
```

**Expected:** Actual token value printed; warning about shell history printed to stderr.

```bash
uv run authsome get github --field status
```

**Expected:** Prints `connected`.

```bash
uv run authsome get github --field scopes
```

**Expected:** Prints the scope list.

```bash
uv run authsome get github --json
```

**Expected:** Connection record as JSON.

---

## 7. Inspect

```bash
uv run authsome inspect github
```

**Expected:** Full provider definition (URLs, flow config, scopes) as JSON; `connections` array shows active connections.

```bash
uv run authsome inspect resend
```

**Expected:** Provider definition with `api_key` config block and `connections` array.

---

## 8. Export

```bash
uv run authsome export github --format env
```

**Expected:** `GITHUB_ACCESS_TOKEN=<value>` printed; warning about shell history.

```bash
uv run authsome export github --format shell
```

**Expected:** `export GITHUB_ACCESS_TOKEN=<value>`.

```bash
uv run authsome export github --format json
```

**Expected:** `{"GITHUB_ACCESS_TOKEN": "<value>"}`.

---

## 9. Proxy Run

```bash
# Verify proxy env vars are injected
uv run authsome run -- env | grep -E 'HTTP_PROXY|HTTPS_PROXY|AUTHSOME_PROXY_MODE'
```

**Expected:**
- `HTTP_PROXY` and `HTTPS_PROXY` set to the local proxy address
- `AUTHSOME_PROXY_MODE=true`

```bash
# Verify dummy credential placeholders are set
uv run authsome run -- env | grep -E 'GITHUB_ACCESS_TOKEN|RESEND_API_KEY'
```

**Expected:** Both set to `authsome-proxy-managed` (real credentials are never in the child environment).

```bash
# Make a real API call through the proxy
uv run authsome run --quiet curl -s https://api.github.com/user
```

**Expected:** JSON response from GitHub with `login` field; no proxy log noise (suppressed by `--quiet`).

```bash
# Multi-provider: both providers injected in one session
uv run authsome run --quiet curl -s https://api.resend.com/domains
```

**Expected:** Valid JSON response from Resend.

---

## 10. Log

```bash
uv run authsome log
```

**Expected:** Human-readable table of recent audit entries with columns `Timestamp`, `Event`, `Provider`, `Status`. Shows "No audit entries found." if empty.

```bash
uv run authsome log -n 5
```

**Expected:** Last 5 entries only (same table format).

```bash
uv run authsome log -n 5 --json
```

**Expected:** JSON object with `v`, `log_file` path, and `entries` array of parsed audit event objects, each with `timestamp`, `event`, `provider`, `status`.

```bash
uv run authsome log --raw -n 10
```

**Expected:** Last 10 lines of the raw client debug log (loguru format).

---

## 11. Connection Management

```bash
uv run authsome set-default github default
```

**Expected:** Confirmation that `default` is now the default connection for `github`.

---

## 12. Custom Provider Registration

```bash
cat > /tmp/test-provider.json << 'EOF'
{
  "name": "test-custom",
  "display_name": "Test Custom",
  "auth_type": "api_key",
  "flow": "api_key",
  "api_key": {
    "header_name": "X-Test-Key"
  }
}
EOF

uv run authsome register /tmp/test-provider.json
```

**Expected:** Confirmation prompt → provider registered. No `api_url` means no reachability check.

```bash
uv run authsome inspect test-custom
```

**Expected:** Provider definition printed as JSON; `connections` is empty.

```bash
uv run authsome list | grep test-custom
```

**Expected:** Listed under `custom` source, `not_connected`.

```bash
# Register again to test --force (overwrites without prompting)
uv run authsome register /tmp/test-provider.json --force
```

**Expected:** Registers immediately, no confirmation prompt, no error.

```bash
uv run authsome remove test-custom
```

**Expected:** `Removed provider test-custom.`

```bash
uv run authsome list | grep test-custom
```

**Expected:** No output (provider gone).

---

## 13. Logout and Revoke

```bash
# Logout removes local record only
uv run authsome logout github
uv run authsome list  # github → not_connected

# Re-login
uv run authsome login github

# Revoke removes local record and calls provider revocation endpoint
uv run authsome revoke github
uv run authsome list  # github → not_connected
```

---

## 14. Daemon

```bash
uv run authsome daemon status
```

**Expected:** JSON showing `running: true`, health checks all `ok`, PID, and log file path. The `health` block includes `version`, `mode`, `encryption_backend`.

```bash
uv run authsome daemon stop
uv run authsome daemon status
```

**Expected:** "Daemon stopped successfully"; `running: false` after stop.

> **Note:** `daemon stop` only works when the daemon was started by `daemon start` (a managed daemon with a PID record). If the daemon is running without a PID record (e.g. after `rm -rf ~/.authsome`), stop is a no-op. Kill the process manually: `kill $(lsof -ti :7998)`.

```bash
uv run authsome daemon start
uv run authsome daemon status
```

**Expected:** "Daemon started successfully"; `running: true` after start.

---

## 15. Global Flags

```bash
# Quiet: suppress informational output
uv run authsome --quiet list
```

**Expected:** Provider table only; no "Providers: N total" banner.

```bash
# No color: plain text output
uv run authsome --no-color list
```

**Expected:** Same table without ANSI color codes.

```bash
# Verbose: debug logging to stderr
uv run authsome --verbose get github
```

**Expected:** DEBUG log lines on stderr in addition to normal stdout output.

---

## 16. Error Handling

```bash
# Non-existent provider
uv run authsome login doesnotexist 2>&1; echo "exit: $?"
```

**Expected:** `ProviderNotFoundError`, exit code `4`.

```bash
uv run authsome inspect doesnotexist 2>&1; echo "exit: $?"
```

**Expected:** `ProviderNotFoundError`, exit code `4`.

```bash
uv run authsome logout doesnotexist 2>&1; echo "exit: $?"
```

**Expected:** `ProviderNotFoundError`, exit code `4`.

```bash
# Missing required argument
uv run authsome get 2>&1; echo "exit: $?"
```

**Expected:** Usage error, exit code `2`.

```bash
# Get on a disconnected provider
uv run authsome logout resend
uv run authsome get resend 2>&1; echo "exit: $?"
```

**Expected:** `ConnectionNotFoundError`, exit code `3`.

---

## Cleanup

```bash
uv run authsome daemon stop
rm -rf ~/.authsome
```

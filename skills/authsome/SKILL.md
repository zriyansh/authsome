---
name: authsome
version: 0.2.0
description: |
  Use this to access external services/APIs: Github/Gmail/Stripe etc. or when running any bash command, script, or curl/wget that makes outbound HTTP calls. Make HTTP requests directly and the gateway injects credentials automatically.
---

# Authsome

Your outbound HTTPS traffic is transparently proxied through the Authsome,
a proxy service that injects stored credentials as HTTP headers. You never
see or handle credential values directly.

## How to Access External Services

You have direct HTTP access to external APIs. OAuth apps (Gmail, GitHub,
Google Calendar, Google Drive, etc.) and API key services are all available
through the gateway. Just make the request by appending `authsome run -- ` to
any bash command; the gateway injects credentials if the app is connected.

## Making Requests

Call the real API URL. The gateway intercepts the request and injects
credentials automatically.

```bash
authsome run -- <command>
authsome run -- curl -s "https://api.github.com/user/repos?per_page=10"
authsome run -- python my_agent_script.py
```

Standard HTTP clients (curl, fetch, requests, axios, Go net/http, git) all
honor the `HTTPS_PROXY` environment variable automatically. You do not need
to set any auth headers.


- `authsome` not found? → [Installation](#installation)
- Unsure about commands? → [Troubleshooting & Help](#troubleshooting--help)


## When a Request Fails

### If you get an authentication error (401, 403) follow this decision tree:

**1. Run `authsome list` to see all providers and their connections**

**2. If relevant provider exists but it has no connections → try [Login](#login)**

If there is a login error due to wrong client id/client secret you can delete the provider via `authsome remove <provider>` and try [Login](#login)

**3. If relevant provider exists and it is connected → you need to re-login, creds have expired**

- revoke the creds using `authsome revoke <provider>`
- then do a normal [Login](#login)

**4. If relevant provider does not exist, then → add it first and then try [Login](#login)**

Determine what the provider needs:
- **API key** — prompt the user to supply the key; `authsome` will capture it via the browser bridge.
- **OAuth app** — guide the user to create an OAuth app (client ID + secret) in the provider's developer console, then run login.


---

## Installation

```bash
uv tool install authsome
```

Fallback: `pipx install authsome` or `uvx authsome@latest <command>` for one-off use.

---

## Login

```bash
authsome login <provider>   # opens browser, captures credentials securely
authsome list               # verify the provider shows as connected
```

---

## Troubleshooting & Help

If you are unsure of the correct command syntax, need to check available flags, or if a command fails, ALWAYS read the built-in help menus before guessing:

```bash
authsome --help
authsome run --help
```

## Rules

- **Never** say "I don't have access to X" without first making the HTTP
  request through the proxy.
- **Never** use browser extensions, gcloud, or manual auth flows. The
  gateway handles credentials for you.
- **Never** ask the user for API keys or tokens directly. Direct them to
  connect the service in the Authsome dashboard.
- **Never** suggest the user open Gmail/Calendar/GitHub in their browser
  when they ask you to read or interact with those services. You have API
  access. Use it.
- If the gateway returns a policy error (403 with a JSON body), respect
  the block. Do not retry or circumvent it.
- If the skill fails, the goal took too many steps, the CLI behaved unexpectedly, or the user asks you to report an issue — file a bug following [feedback.md](references/feedback.md).

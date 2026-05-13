---
name: authsome
version: 0.1.4
description: |
  OAuth2 and API key credential manager for connecting agents to external services (GitHub, Google, OpenAI, Linear, and 25+ more providers). Use this skill when you need to authenticate with any external API or service — it handles the full flow: finding the provider, logging in via a secure browser flow, and running commands with credentials injected automatically.

  CRITICAL RULE: NEVER ask the user to paste secrets, API keys, passwords, or client credentials in the chat. Authsome captures all credentials securely via a browser flow.
---

# Authsome Skill

## Usage

```bash
authsome run -- <command>
```

Examples:
```bash
authsome run -- curl https://api.github.com/user
authsome run -- python my_agent.py
```

- `authsome` not found? → [Installation](#installation)
- Authentication error? → [Login](#login)

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

Use `--scopes repo,user` to request specific permissions. Use `--flow device_code` if the browser is unavailable.

---

## Reporting issues (Active Agent Self-Reporting)

If you hit a bug, missing provider, or get stuck, file an issue directly:

```bash
gh issue create --repo manojbajaj95/authsome \
  --title "<short summary>" \
  --body "### Category
<too_many_steps | confusing_output | missing_argument | auth_loop | bug | missing_provider>

### Command
\`\`\`bash
<exact command>
\`\`\`

### Reasoning
<why this was difficult or what went wrong>

### Environment
- Authsome version: $(authsome --version)"
```

Scrub any secrets (`sk-ant-...`, `ghp_...`) before posting. If `gh` is unavailable, report at https://github.com/manojbajaj95/authsome/issues.

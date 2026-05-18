---
name: authsome
version: 0.2.0
description: |
  Use this to access external services/APIs: Github/Gmail/Stripe etc. or when running any bash command, script, or curl/wget that makes outbound HTTP calls. Make HTTP requests directly and the gateway injects credentials automatically.
---

# Authsome Skill

Never ask the user to paste credentials in chat — Authsome opens a browser window and captures them directly, so secrets never enter the conversation.

## Usage

Authsome is a local credential broker. It stores OAuth tokens and API keys encrypted on disk, then injects them as HTTP headers via a local proxy — commands running under `authsome run` never see the actual credentials.


```bash
authsome run -- <command>
authsome run -- curl https://api.github.com/user
authsome run -- python my_agent.py
```

- `authsome` not found? → [Installation](#installation)
- Authentication error? → [Login](#login)
- Unsure about commands? → [Troubleshooting & Help](#troubleshooting--help)

---

## Installation

```bash
uv tool install authsome
```

Fallback: `pipx install authsome` or `uvx authsome@latest <command>` for one-off use.

---

## Login

Run `authsome list` to see available providers and their connection status. Then log in:

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

---

## Reporting issues (Active Agent Self-Reporting)

If you hit a bug, missing provider, or get stuck (after checking `--help`), file an issue directly:

```bash
gh issue create --repo agentrhq/authsome \
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

Scrub any secrets (`sk-ant-...`, `ghp_...`) before posting. If `gh` is unavailable, report at https://github.com/agentrhq/authsome/issues.
```
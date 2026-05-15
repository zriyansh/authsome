<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/authsome-logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/authsome-logo-light.svg">
    <img alt="Authsome" src="assets/authsome-logo-light.svg" height="60">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/authsome/"><img src="https://img.shields.io/pypi/v/authsome.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/authsome/"><img src="https://img.shields.io/pypi/pyversions/authsome.svg" alt="Python 3.13+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://pypi.org/project/authsome/"><img src="https://img.shields.io/pypi/dm/authsome.svg" alt="PyPI downloads"></a>
  <a href="https://github.com/agentrhq/authsome/actions/workflows/test.yml"><img src="https://github.com/agentrhq/authsome/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://codecov.io/gh/agentrhq/authsome"><img src="https://codecov.io/gh/agentrhq/authsome/branch/main/graph/badge.svg" alt="codecov"></a>
  <a href="https://discord.gg/9YP2C9tvMp"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <b>Local-first credential broker and vault for AI Agents</b>
</p>

<p align="center">
  <a href="https://authsome.agentr.dev/docs">Docs</a> ·
  <a href="https://authsome.agentr.dev">Website</a> ·
  <a href="https://discord.gg/9YP2C9tvMp">Discord</a> ·
  <a href="https://github.com/agentrhq/authsome/issues">Issues</a>
</p>

---

An open-source credential broker that sits between your agents and the services they call. Instead of sharing credentials with every agent, log in once via OAuth2 or API keys. Authsome stores credentials securely and injects them via an HTTP proxy. You get one place to manage access, rotate keys, and see what every agent is doing.

**44 bundled providers** out of the box: 13 OAuth2 and 31 API key. [See the full list](https://authsome.agentr.dev/docs/reference/bundled-providers).

---

## Demo

https://github.com/user-attachments/assets/27f9b229-baf4-4889-be9a-378a133654dc

---

## Why Agents Need Authsome

Agents run beyond interactive sessions. They live in CI, over SSH, in cron jobs, in background workers, and in parallel pipelines. They need API access that survives without a human in the loop.

Hardcoded environment tokens leak or go stale, and building auth flow logic, token storage, refresh handling, and per-provider config into every project rebuilds the same plumbing every time.

Authsome is the local credential layer agents call at runtime.

- **No credential sprawl.** One encrypted store. Every provider, every agent, one place.
- **No SaaS, no privacy trade-off.** Credentials never leave your machine. Eliminates credential exfiltration risks as agents never see them.
- **No browser required at runtime.** Setup can use browser PKCE, device code, or a browser bridge for secure API key entry. After that, agents run headlessly.

---

## How It Works

The CLI is the agent's interface: setup once, then inject fresh credentials whenever a tool runs.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/authsome-how-it-works-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/authsome-how-it-works-light.svg">
  <img alt="Authsome Architecture" src="assets/authsome-how-it-works-light.svg" width="100%">
</picture>

Authenticate once:

```bash
uvx authsome login github
```

Then agents get valid credentials on demand:

```bash
uvx authsome get github --field access_token --show-secret
# → ghu_...

export $(uvx authsome export github)
# → sets GITHUB_ACCESS_TOKEN in current shell

uvx authsome run python my_agent.py
# runs behind a local auth proxy that injects headers at request time
# without exposing secrets in the child process environment.
# matched automatically via provider api_url (e.g. api.openai.com)
```

Credentials are stored locally, encrypted at rest, and refreshed before expiry. No server. No account. No cloud.

---

## Why Authsome

| | authsome | Hardcoded env tokens | DIY |
|--|:--------:|:--------------------:|:---:|
| Automatic token refresh | ✅ | ❌ | build it |
| OAuth2 + API keys | ✅ | ❌ | build it |
| Runtime headless use | ✅ | ✅ | varies |
| Local, no SaaS dependency | ✅ | ✅ | ✅ |
| Built-in providers, zero config | ✅ | ❌ | ❌ |
| Multi-account per provider | ✅ | ❌ | build it |

Authsome gives agents one command for a valid token, without scattering long-lived secrets across every project.

---

## Install

Requires Python 3.13+.

```bash
pip install authsome
```

Or run without installing:

```bash
uvx authsome@latest --help
```

## Quick Start

```bash
uvx authsome login github                     # opens browser, completes PKCE flow
uvx authsome login github --flow device_code  # headless: Device Code, works over SSH and CI
uvx authsome login openai                     # secure API key entry via browser bridge
uvx authsome list                             # all connections + token status
```

## Agent Integrations

Authsome ships with adapters for the most common agent frameworks and CLIs:

- [Claude Code](https://authsome.agentr.dev/docs/integrations/agents/claude-code)
- [Codex](https://authsome.agentr.dev/docs/integrations/agents/codex)
- [Cursor](https://authsome.agentr.dev/docs/integrations/agents/cursor)
- [OpenCode](https://authsome.agentr.dev/docs/integrations/agents/opencode)
- [LangChain](https://authsome.agentr.dev/docs/integrations/agents/langchain)
- [LlamaIndex](https://authsome.agentr.dev/docs/integrations/agents/llamaindex)
- [OpenAI Agents SDK](https://authsome.agentr.dev/docs/integrations/agents/openai-agents-sdk)
- [Anthropic SDK](https://authsome.agentr.dev/docs/integrations/agents/anthropic-sdk)

Full list at [authsome.agentr.dev/docs/integrations](https://authsome.agentr.dev/docs/integrations/agents/index).

## Docs

Full documentation lives at **[authsome.agentr.dev/docs](https://authsome.agentr.dev/docs)**.

- [Quickstart](https://authsome.agentr.dev/docs/quickstart)
- [CLI reference](https://authsome.agentr.dev/docs/reference/cli)
- [Architecture](https://authsome.agentr.dev/docs/concepts/architecture)
- [Custom providers](https://authsome.agentr.dev/docs/guides/custom-providers)
- [Troubleshooting](https://authsome.agentr.dev/docs/troubleshooting/doctor)

To preview the docs site locally:

```bash
cd docs/site
npm i -g mint   # requires Node.js >= 20.17.0
mint dev
```

## Community

- **[Discord](https://discord.gg/9YP2C9tvMp)** for questions, help, and showing what you're building.
- **[GitHub Issues](https://github.com/agentrhq/authsome/issues)** for bugs and feature requests.

## Security

Authsome is a credential tool. If you find a vulnerability, please do **not** open a public GitHub issue.

See the [responsible disclosure policy](https://authsome.agentr.dev/docs/security/disclosure) for how to report it privately.

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and the engineering principles we follow.

## Star History

<a href="https://star-history.com/#agentrhq/authsome&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=agentrhq/authsome&type=Date&theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=agentrhq/authsome&type=Date">
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=agentrhq/authsome&type=Date">
  </picture>
</a>

## License

MIT. See [LICENSE](LICENSE).

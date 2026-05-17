# Agentic Eval Runner — Design Spec

**Date:** 2026-05-17
**Status:** Implemented

---

## Problem

Authsome is delivered to end-users as an agent skill. The quality of that skill depends on two things that can't be covered by unit tests:

1. **Skill triggering** — does the skill description cause agents to load the skill when they should?
2. **End-to-end behaviour** — does the agent complete the task correctly across the three credential scenarios?

These evals require running live agents against real prompts, involve human steps (OAuth flows, API key entry), and produce outputs that need LLM-as-judge grading. They don't belong in `pytest`.

---

## Goals

- Run evals from `skills/authsome/evals/evals.json` against live agents.
- Grade results with an LLM judge using plain-English pass criteria.
- Display results as an HTML report matching the skill-creator visual style.
- Handle rate limit errors gracefully (grade partial transcript with a warning, never fail-fast).
- The user triggers runs via the `/run-evals` Claude command, which handles all interaction.

---

## Non-goals

- No integration with `uv run pytest`.
- No parameterisation over skill description variants (test the current SKILL.md as-is).
- No CI automation (human-run, human-supervised).

---

## Pre-session Setup

Before running any evals, the tester follows the setup section in `.claude/commands/run-evals.md`:

1. `uv sync` — install the latest authsome CLI from the repo
2. `uv run authsome doctor` — verify the existing identity is healthy
3. `uv run authsome profile create --json` + `profile use <handle>` — create and switch to a fresh identity for the eval session (preserves real credentials)
4. `uv run authsome list` — confirm the new profile has no connected providers
5. `hermes chat -Q -q "reply with the single word OK" -t ""` — smoke-test hermes (used as LLM judge)

The setup deliberately uses a **fresh identity** rather than wiping state. This preserves the user's real credentials while ensuring tests start from a clean slate.

---

## Test Sequence

The order of evals is intentional — **state carries over between tests**. Running them out of order will produce wrong results.

| ID | Name | State entering | State leaving | Optional |
|---|---|---|---|---|
| 1 | Skill Triggering | no providers connected | no providers connected | no |
| 2 | Scenario 2 — OAuth (github not connected) | github not connected | github connected | no |
| 3 | Scenario 1 — OAuth (github connected) | github connected (from test 2) | github connected | no |
| 4 | Scenario 1 — CLI (gh configured) | gh CLI authenticated locally, github not connected via authsome | same | no |
| 5 | Scenario 3 — API Key (firecrawl not configured) | firecrawl not connected | firecrawl connected | no |
| 6 | Scenario 3 — OAuth (ClickUp not connected) | clickup not connected | clickup connected | no |
| 7 | Agentic Installation and Login | authsome CLI not installed | github connected | **yes** |

Eval 7 is optional and runs last because it requires uninstalling authsome, which invalidates the eval profile's stored credentials.

---

## evals.json Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | int | yes | Unique identifier |
| `name` | string | yes | Short human-readable name |
| `prompt` | string | yes | The task prompt sent to the agent |
| `agent` | string | no | Agent CLI: `hermes`, `claude`, `codex`. Defaults to `claude`. |
| `environment` | string | yes | Pre-conditions required before running. Fed to the LLM judge as context. |
| `outcome` | string | yes | Plain English description of what success looks like. Graded independently. |
| `trajectory_efficiency` | string | no | Expected number of meaningful steps (scaffolding excluded). Omit when not testing efficiency. |
| `requires_human` | bool | yes | Whether the eval requires human action mid-run (OAuth flow, API key entry). |
| `human_instructions` | string | no | Required when `requires_human: true`. Describes what the human should do. |
| `optional` | bool | no | If `true`, skipped by default; included with `--all`. |

`environment` is mandatory because almost every eval depends on a specific credential state, and the LLM judge needs this context to evaluate correctly.

---

## Skill Installation

The authsome skill is installed automatically before each eval run based on the `agent` field:

| Agent | Install location | Rationale |
|---|---|---|
| `hermes` | `~/.hermes/skills/authsome/SKILL.md` | Hermes is tested with its full bundled skill set to replicate real user conditions |
| `claude` / `codex` | `.claude/commands/authsome.md` | Installed as a Claude Code slash command |

---

## Architecture

```
.claude/commands/
  run-evals.md          # /run-evals slash command — orchestrates interactive eval flow

evals/
  run_evals.py          # non-interactive runner: run agent, grade, save results
  generate_report.py    # reads grading.json, writes and opens report.html
  results/              # gitignored
    <timestamp>/
      transcript_<id>.txt   # raw agent stdout+stderr
      grading.json          # accumulated results
      report.html           # generated HTML

skills/authsome/evals/
  evals.json            # eval definitions (7 evals)
```

### Interaction model

The `/run-evals` Claude command owns all user interaction. For each eval it:

1. Runs `authsome list` and shows the current state
2. Compares against the eval's `environment` field and asks the user to confirm or fix
3. Calls `run_evals.py --id N --profile <handle> --run-dir <dir>` once confirmed
4. Shows the verdict and asks before moving to the next eval

`run_evals.py` is fully non-interactive — no `input()` calls. The command manages the profile lifecycle and run directory.

### run_evals.py

**Flags:**
- `--id N` — run only eval with this id
- `--profile HANDLE` — use an existing profile (skip create/teardown; used by the command)
- `--run-dir PATH` — append results to an existing run directory (used by the command)

**Per-eval flow:**
1. Capture `authsome list` output as `authsome_state` (stored in results for the report)
2. Build agent command based on `agent` field
3. Run via `subprocess.Popen` + threading (tees stdout to terminal and captures for transcript)
4. Detect rate limit signals in transcript — emit `[WARNING]`, grade partial transcript anyway
5. Grade with hermes LLM judge
6. Append to `grading.json` (or create it)

### LLM Judge

Uses **hermes** in quiet mode (`hermes chat -Q -q <prompt> -t ""`). The full system prompt and grading criteria are included in the user message (hermes has no separate system prompt flag). The judge returns JSON with two independent verdicts:

```json
{
  "outcome": {"passed": true, "evidence": "one sentence from the transcript"},
  "trajectory_efficiency": {"passed": null, "evidence": "not evaluated"}
}
```

`trajectory_efficiency.passed` is `null` when the criterion is absent from the eval.

A preflight check runs `hermes chat -Q -q "reply with the single word OK" -t ""` before any evals to catch auth/config issues early.

### generate_report.py

Reads `grading.json`, generates `report.html`, opens in the default browser.

**HTML style** matches skill-creator:
- Fonts: Poppins (headings), Lora (body)
- Colors: `#141413` header, `#faf9f5` bg, `#788c5d` pass green, `#c44` fail red, `#e8e6dc` borders
- Per-eval card: id, name, agent badge, human badge, outcome/trajectory icons, evidence quotes
- Collapsible sections: environment, authsome state at start
- Summary bar: passed / failed / skipped / total

---

## grading.json Format

```json
{
  "skill_name": "authsome",
  "timestamp": "2026-05-17T13:24:00",
  "summary": {"passed": 1, "failed": 0, "skipped": 0, "total": 1},
  "results": [
    {
      "id": 1,
      "name": "Skill Triggering",
      "prompt": "Can you list my last 5 starred repositories on GitHub?",
      "agent": "hermes",
      "environment": "hermes installed with authsome skill available...",
      "authsome_state": "output of authsome list at start of eval",
      "requires_human": false,
      "rate_limited": false,
      "outcome": {
        "passed": true,
        "evidence": "Transcript shows skill_view called with name=authsome"
      },
      "trajectory_efficiency": {
        "passed": null,
        "evidence": "not evaluated"
      }
    }
  ]
}
```

---

## Usage

```bash
# Recommended: via Claude command (handles state checks interactively)
/run-evals
/run-evals --id 1
/run-evals --all    # includes optional eval 7

# Direct batch run (no interactive state checks):
uv run python evals/run_evals.py
uv run python evals/run_evals.py --id 1

# Generate report from a previous run:
uv run python evals/generate_report.py evals/results/<timestamp>/grading.json
```

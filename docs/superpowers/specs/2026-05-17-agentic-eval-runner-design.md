# Agentic Eval Runner — Design Spec

**Date:** 2026-05-17
**Scope:** Test 1 (Skill Triggering) with architecture extensible to all 7 planned evals.

---

## Problem

Authsome is delivered to end-users as an agent skill. The quality of that skill depends on two things that can't be covered by unit tests:

1. **Skill triggering** — does the skill description cause agents to load the skill when they should?
2. **End-to-end behaviour** — does the agent complete the task correctly across the three credential scenarios?

These evals require running live agents against real prompts, involve rate limits that require human intervention, and produce outputs that need LLM-as-judge grading. They don't belong in `pytest`.

---

## Goals

- Run evals from `skills/authsome/evals/evals.json` against live agents.
- Grade results with an LLM judge using plain-English pass criteria.
- Display results as an HTML report matching the skill-creator visual style.
- Handle rate limit errors gracefully (skip + human message, never fail-fast).
- Start with Test 1 (Skill Triggering via Hermes); architecture supports all 7 tests.

---

## Non-goals

- No integration with `uv run pytest`.
- No parameterisation over skill description variants (test the current SKILL.md as-is).
- No CI automation (human-run, human-supervised).

---

## Setup

Before running any evals, the tester follows `evals/setup.md` to bring the machine to a known clean state. This ensures every eval starts from a predictable authsome installation with no leftover credential state from previous runs.

`evals/setup.md` covers:
1. Fresh install: `uv tool install --reinstall authsome` (or `uv tool uninstall authsome && uv tool install authsome`)
2. Wipe state: `rm -rf ~/.authsome`
3. Initialise: `authsome init`
4. Verify: `authsome doctor` — must exit `0` with all checks `ok`
5. Confirm no providers are connected: `authsome list`

The setup deliberately leaves **no providers connected**. Each eval is responsible for the credential state it needs, and the test sequence is ordered so that state built up by one eval is reused by the next (see Test Sequence below).

---

## Test Sequence

The order of evals is intentional — **state carries over between tests**. Running them out of order will produce wrong results.

| Order | ID | Name | State entering | State leaving |
|---|---|---|---|---|
| 1 | 1 | Skill Triggering | no providers connected | no providers connected |
| 2 | 2 | Agentic Installation and Login | authsome fresh, no providers | github connected |
| 3 | 3 | Scenario 2 — OAuth (github not connected) | github disconnected (logout after test 2) | github connected |
| 4 | 4 | Scenario 1 — OAuth (github connected) | github connected (from test 3) | github connected |
| 5 | 5 | Scenario 1 — CLI (gh configured) | gh CLI authenticated locally | gh CLI authenticated locally |
| 6 | 6 | Scenario 3 — API Key (firecrawl not connected) | firecrawl not connected | firecrawl connected |
| 7 | 7 | Scenario 3 — OAuth (ClickUp not connected) | clickup not connected | clickup connected |

> Between tests 2 and 3, the human should run `authsome logout github` so that test 3 starts with github disconnected.

---

## evals.json Schema

Each eval object has the following fields:

**Scenario 1 example (fully automated):**
```json
{
  "id": 3,
  "prompt": "list my open GitHub issues assigned to me",
  "agent": "claude",
  "environment": "github is connected",
  "outcome": "The agent successfully fetches and displays the user's open GitHub issues",
  "trajectory_efficiency": "1 meaningful step: calls the GitHub API directly via authsome run without checking auth state first. Example: authsome run -- curl -s \"https://api.github.com/issues?per_page=50&state=open&filter=assigned\"",
  "requires_human": false
}
```

**Scenario 2 example (human-in-the-loop):**
```json
{
  "id": 4,
  "prompt": "list all my GitHub repos",
  "agent": "claude",
  "environment": "github is NOT connected",
  "outcome": "The agent successfully fetches and displays the user's GitHub repos after the user connects GitHub",
  "trajectory_efficiency": "3 meaningful steps: (1) tries the GitHub API directly via authsome run, (2) learns github is not connected and forwards the auth link to the user, (3) after user confirms connected, retries and succeeds",
  "requires_human": true,
  "human_instructions": "When the agent shares a GitHub auth link, open it in your browser and complete the OAuth flow. Then type 'done' to continue."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | int | yes | Unique identifier |
| `prompt` | string | yes | The task prompt sent to the agent |
| `agent` | string | no | Which agent CLI to use: `hermes`, `claude`, `codex`. Defaults to `claude`. |
| `environment` | string | **yes** | Pre-conditions required before running (e.g. "github connected, firecrawl not connected"). Fed to the LLM judge as context. |
| `outcome` | string | yes | Plain English description of what a successful result looks like. The LLM judge evaluates this independently of efficiency. |
| `trajectory_efficiency` | string | no | Plain English description of the expected number of meaningful steps and what each one is. Scaffolding steps (skill loading, reading `--help`, version checks) are excluded from the count. Omit for evals where step efficiency is not being tested. |
| `requires_human` | bool | yes | Whether the eval requires human intervention mid-run (e.g. completing an OAuth flow or entering an API key). |
| `human_instructions` | string | no | Required when `requires_human: true`. Describes exactly what the human should do when the runner pauses. |

`environment` is mandatory because almost every eval depends on a specific credential state, and the LLM judge needs this context to evaluate correctly.

`requires_human: false` evals are fully automated. `requires_human: true` evals pause the runner mid-execution and wait for human input — see the Human-in-the-Loop section below.

---

## Skill Installation for Testing

The authsome skill must be installed in the agent before each eval run. The install mode is determined by the `agent` field — it is not a per-eval parameter because the reason for each mode is structural, not case-by-case:

| Agent | Install mode | Rationale |
|---|---|---|
| `hermes` | **Global** (`hermes skills install`) | Hermes is tested with its full bundled skill set to replicate real user conditions. The skill must compete against other skills for triggering — a local-only install would bypass this. |
| `claude`, `codex`, or default | **Local** (`evals/tmp/skills/authsome/`) | Other agents are tested in isolation. A local install in a temporary folder keeps the test environment clean and avoids polluting the user's global skill config. |

`run_evals.py` handles installation automatically before running evals:
- For `hermes`: runs `hermes skills install <path-to-SKILL.md>` (or equivalent) to update the globally installed authsome skill.
- For others: copies `skills/authsome/SKILL.md` into `evals/tmp/skills/authsome/SKILL.md` and passes the skills directory to the agent CLI.

`evals/tmp/` is gitignored.

---

## Architecture

```
evals/
  setup.md              # human-readable setup guide: fresh install + clean state
  run_evals.py          # entry point: runs agents, grades, writes results/
  generate_report.py    # reads grading.json, writes report.html, opens browser
  tmp/                  # gitignored — local skill installs for non-hermes agents
    skills/authsome/SKILL.md
  results/              # gitignored
    <timestamp>/
      transcript_<id>.txt   # raw agent stdout+stderr
      grading.json          # LLM judge output
      report.html           # generated HTML
```

### run_evals.py

1. Load `skills/authsome/evals/evals.json`.
2. Install the skill for the appropriate agent (see Skill Installation section above).
3. For each eval:
   a. Print environment reminder so the human can verify pre-conditions are met.
   b. Build the agent command based on `agent` field:
      - `hermes` → `hermes chat -q "<prompt>" --yolo --max-turns 3 -v`
      - `claude` → `claude -p "<prompt>" --skills evals/tmp/skills` (default)
      - `codex` → `codex "<prompt>"`
   c. If `requires_human: true` → print the environment reminder and `human_instructions`, then prompt `Press Enter when ready to start...` before launching the agent.
   d. Run via `subprocess.run`, capture combined stdout+stderr as the transcript.
   e. On rate limit detected in output → print `[SKIPPED] Rate limit hit — switch model and retry`, mark result `skipped`, continue.
   f. Call Claude API (LLM judge) with:
      - System: grader instructions
      - User: transcript + `pass_criteria` + `environment`
   g. Parse judge response into `passed: bool` + `evidence: str`.
3. Write `results/<timestamp>/grading.json`.
4. Print console summary (pass/skip/fail counts).
5. Offer to open report: `uv run python evals/generate_report.py results/<timestamp>/grading.json`.

### Human-in-the-Loop Evals

Some evals (Scenario 2 and 3) cannot be fully automated because the agent will pause mid-task and ask the user to complete an OAuth flow or enter an API key. The runner handles this as follows:

1. **Before the agent starts:** print the `human_instructions` and the `environment` reminder so the human knows what state to set up and what to expect.
2. **Prompt `Press Enter when ready to start...`** — human confirms pre-conditions are met.
3. **Agent runs normally** — the agent surfaces the auth link or key prompt to the user in the terminal.
4. **Human completes the action** (e.g. OAuth in browser, pastes API key).
5. **Agent resumes** and completes the task.
6. The full transcript (including the human-assisted steps) is captured and sent to the LLM judge, which evaluates it against `pass_criteria` including the expected step count.

The runner does not automate the credential flow itself — that is intentional. These evals test the full user experience including the handoff to the browser.

### LLM Judge

Uses the Claude API (Haiku for cost) with a terse system prompt:

> You are an eval grader. You receive an agent transcript, environment pre-conditions, an outcome criterion, and a trajectory_efficiency criterion. Return JSON with two independent verdicts:
> ```json
> {
>   "outcome": {"passed": true/false, "evidence": "<one sentence from the transcript>"},
>   "trajectory_efficiency": {"passed": true/false, "evidence": "<one sentence from the transcript>"}
> }
> ```
> Grade outcome and trajectory_efficiency independently — a task can succeed with a poor trajectory or fail despite a clean trajectory. When counting steps for trajectory_efficiency, ignore scaffolding: skill loading, reading `--help`, version checks, and similar overhead do not count. Only task-relevant actions count (API calls, auth flows, presenting results). Be strict: the burden of proof to pass is on the transcript.

### generate_report.py

Reads `grading.json`, generates `report.html`, opens it in the default browser.

**HTML style** matches skill-creator exactly:
- Fonts: Poppins (headings), Lora (body)
- Colors: `#141413` header bg, `#faf9f5` page bg, `#788c5d` pass green, `#c44` fail red, `#e8e6dc` borders
- One row per eval: ID, agent, prompt, environment (collapsed), pass/fail icon, LLM evidence quote
- Summary bar at top: `X passed / Y failed / Z skipped out of N`

---

## grading.json Format

```json
{
  "skill_name": "authsome",
  "timestamp": "2026-05-17T13:24:00",
  "summary": {"passed": 1, "failed": 1, "skipped": 1, "total": 3},
  "results": [
    {
      "id": 1,
      "prompt": "how many repos i have on github",
      "agent": "hermes",
      "environment": "hermes installed with authsome skill available",
      "requires_human": false,
      "outcome": {
        "passed": true,
        "evidence": "Transcript shows skill_view called with name=authsome at 13:24:08"
      },
      "trajectory_efficiency": {
        "passed": true,
        "evidence": "Agent called skill_view then ran authsome run -- curl in 1 meaningful step"
      }
    },
    {
      "id": 2,
      "prompt": "list all my GitHub repos",
      "agent": "claude",
      "environment": "github is NOT connected",
      "requires_human": true,
      "outcome": {
        "passed": true,
        "evidence": "Transcript shows repos listed successfully after user completed OAuth"
      },
      "trajectory_efficiency": {
        "passed": true,
        "evidence": "3 meaningful steps: API call → auth link forwarded → retry succeeded"
      }
    },
    {
      "id": 3,
      "prompt": "...",
      "status": "skipped",
      "evidence": "Rate limit hit"
    }
  ]
}
```

---

## Usage

```bash
# Run all evals
uv run python evals/run_evals.py

# Run a specific eval by id
uv run python evals/run_evals.py --id 1

# Generate/open report from a previous run
uv run python evals/generate_report.py evals/results/20260517_132400/grading.json
```

---

## Test 1: Skill Triggering (initial implementation)

**What it tests:** Does the authsome SKILL.md description cause Hermes to call `skill_view(name="authsome")` when given a task that implicitly requires external API access?

**Detection signal:** Grep the verbose hermes transcript for `skill_view.*authsome`.

**Why Hermes specifically:** Hermes bundles many skills and truncates descriptions in its prompt. If the skill triggers in Hermes, it will trigger in simpler single-skill environments too.

**Existing evals.json prompts used:** IDs 1–4 from `skills/authsome/evals/evals.json`. ID 4 ("Can you list my last 5 starred repositories on GitHub?") is the key implicit-trigger case.

The `pass_criteria` for all Test 1 evals is a variation of:
> "The agent recognises it needs external API access and loads the authsome skill via skill_view without being explicitly told to use authsome."

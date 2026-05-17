# Agentic Eval Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone eval runner that executes authsome skill tests against live agents, grades results with an LLM judge, and renders an HTML report.

**Architecture:** A two-script system — `run_evals.py` runs each eval against the appropriate agent CLI, captures the transcript, and calls the Claude API as a judge; `generate_report.py` turns the resulting `grading.json` into a styled HTML report. Evals are defined in `skills/authsome/evals/evals.json` and are completely separate from pytest.

**Tech Stack:** Python 3.11+, `anthropic` SDK (added as dev dependency), `subprocess` + threading for agent capture, plain HTML/CSS for reports (no frontend framework).

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `evals/setup.md` | Create | Human-readable pre-run setup guide: fresh install + clean state |
| `skills/authsome/evals/evals.json` | Rewrite | All 7 eval definitions in execution order |
| `evals/.gitignore` | Create | Ignore `tmp/` and `results/` |
| `evals/run_evals.py` | Create | Runner: install skill, run agent, grade with LLM |
| `evals/generate_report.py` | Create | Read grading.json, write and open report.html |
| `pyproject.toml` | Modify | Add `anthropic` to dev dependencies |

---

## Task 0: Create evals/setup.md

**Files:**
- Create: `evals/setup.md`

- [ ] **Step 1: Write setup.md**

```markdown
# Eval Setup Guide

Run this before every eval session. It brings the machine to a known clean state so tests start from predictable authsome installation with no leftover credential state.

## 1. Fresh install

If authsome is already installed, reinstall to get the latest version:

\`\`\`bash
uv tool install --reinstall authsome
\`\`\`

If not yet installed:

\`\`\`bash
uv tool install authsome
\`\`\`

Verify:

\`\`\`bash
authsome --version
\`\`\`

## 2. Wipe state

Remove all existing authsome state (identities, credentials, config):

\`\`\`bash
rm -rf ~/.authsome
\`\`\`

## 3. Initialise

\`\`\`bash
authsome init
\`\`\`

Expected: prints your new identity handle and DID.

## 4. Verify

\`\`\`bash
authsome doctor
\`\`\`

Expected: exit code `0`, all checks `ok`.

## 5. Confirm no providers are connected

\`\`\`bash
authsome list
\`\`\`

Expected: all providers show `not_connected`. If any show `connected`, run `authsome logout <provider>` for each.

---

## Between-test state notes

The eval sequence is ordered so that credential state built by one test is reused by the next. See the Test Sequence table in the design spec. The one manual step between tests is:

- **After test 2 (Agentic Installation and Login):** run `authsome logout github` so that test 3 (Scenario 2) starts with github disconnected.
```

- [ ] **Step 2: Commit**

```bash
git add evals/setup.md
git commit -m "docs(evals): add setup.md — pre-run fresh install guide"
```

---

## Task 1: Rewrite evals.json with new schema

**Files:**
- Modify: `skills/authsome/evals/evals.json`

- [ ] **Step 1: Replace evals.json with the 7 new evals in execution order**

The order is intentional — state from one test carries into the next. Write the following to `skills/authsome/evals/evals.json`:

```json
{
  "skill_name": "authsome",
  "evals": [
    {
      "id": 1,
      "name": "Skill Triggering",
      "prompt": "Can you list my last 5 starred repositories on GitHub?",
      "agent": "hermes",
      "environment": "hermes is installed with the authsome skill available alongside its full set of bundled skills. No GitHub connection is required — this test only checks whether the skill is loaded.",
      "outcome": "The agent loads the authsome skill (calls skill_view with name=authsome) without being explicitly told to use authsome.",
      "requires_human": false
    },
    {
      "id": 2,
      "name": "Agentic Installation and Login",
      "prompt": "I want to connect GitHub so my agent can access my repos. Please set everything up.",
      "agent": "claude",
      "environment": "authsome CLI is NOT installed (simulate fresh device: run `uv tool uninstall authsome` before this test). The authsome skill is available via .claude/commands/authsome.md.",
      "outcome": "The agent installs authsome via `uv tool install authsome`, runs `authsome init` to create a local identity, and completes the GitHub OAuth login flow so that `authsome list` shows github as connected.",
      "trajectory_efficiency": "3 meaningful steps: (1) installs authsome via uv tool install, (2) runs authsome init, (3) runs authsome login github and completes OAuth in browser.",
      "requires_human": true,
      "human_instructions": "When the browser opens for GitHub OAuth authorization, complete the flow and return to the terminal. The agent will continue automatically once authsome login succeeds. After this test completes, run `authsome logout github` to reset state for the next test."
    },
    {
      "id": 3,
      "name": "Scenario 2 - OAuth (github not connected)",
      "prompt": "List all my GitHub repos",
      "agent": "claude",
      "environment": "github is NOT connected via authsome (authsome list shows github as not_connected). gh CLI is not authenticated. Comes after test 2 — run `authsome logout github` first.",
      "outcome": "The agent successfully fetches and displays the user's GitHub repositories after the user completes the OAuth flow.",
      "trajectory_efficiency": "3 meaningful steps: (1) attempts the GitHub API via authsome run and receives a not-connected error, (2) runs authsome login github and presents the browser auth flow to the user, (3) after OAuth completes, retries the API call and returns results.",
      "requires_human": true,
      "human_instructions": "When the browser opens for GitHub OAuth authorization, complete the flow and return to the terminal. The agent will retry the API call automatically."
    },
    {
      "id": 4,
      "name": "Scenario 1 - OAuth (github connected)",
      "prompt": "List all my GitHub repos",
      "agent": "claude",
      "environment": "github is connected via authsome (authsome list shows github as connected — state carried over from test 3).",
      "outcome": "The agent successfully fetches and displays the user's GitHub repositories.",
      "trajectory_efficiency": "1 meaningful step: calls the GitHub repos API directly via authsome run -- curl https://api.github.com/user/repos without first running authsome list or authsome login.",
      "requires_human": false
    },
    {
      "id": 5,
      "name": "Scenario 1 - CLI (gh locally configured)",
      "prompt": "List all my GitHub repos",
      "agent": "claude",
      "environment": "gh CLI is locally authenticated (gh auth status shows logged in). authsome is available but GitHub is NOT connected via authsome (run `authsome logout github` first).",
      "outcome": "The agent successfully fetches and displays the user's GitHub repositories using gh CLI.",
      "trajectory_efficiency": "1 meaningful step: runs gh repo list directly without attempting to set up authsome for GitHub.",
      "requires_human": false
    },
    {
      "id": 6,
      "name": "Scenario 3 - API Key (firecrawl not configured)",
      "prompt": "Scrape the content of https://firecrawl.dev using Firecrawl",
      "agent": "claude",
      "environment": "firecrawl is NOT connected via authsome (authsome list shows firecrawl as not_connected or absent). No FIRECRAWL_API_KEY environment variable is set.",
      "outcome": "The agent successfully scrapes the page using Firecrawl after the user provides an API key through the authsome login flow.",
      "trajectory_efficiency": "3 meaningful steps: (1) attempts to use Firecrawl via authsome run and receives a not-connected error, (2) runs authsome login firecrawl which opens a browser form for the API key, (3) after the user submits the key, retries the scrape and returns results.",
      "requires_human": true,
      "human_instructions": "When the browser opens a form asking for a Firecrawl API key, paste your API key and submit. The agent will continue automatically."
    },
    {
      "id": 7,
      "name": "Scenario 3 - OAuth (ClickUp not connected, provider may need registration)",
      "prompt": "Get my assigned tasks from ClickUp",
      "agent": "claude",
      "environment": "ClickUp is NOT connected via authsome. ClickUp may not be in the bundled provider list — the agent may need to register it as a custom OAuth provider first.",
      "outcome": "The agent successfully fetches and displays the user's assigned ClickUp tasks after setting up the provider and completing OAuth.",
      "trajectory_efficiency": "4 meaningful steps: (1) checks authsome list and finds ClickUp absent or not connected, (2) registers ClickUp as a custom OAuth provider using authsome register, (3) runs authsome login clickup and completes OAuth in browser, (4) calls the ClickUp API via authsome run and returns results.",
      "requires_human": true,
      "human_instructions": "When the browser opens for ClickUp OAuth authorization, complete the flow and return to the terminal. The agent will continue automatically."
    }
  ]
}
```

- [ ] **Step 2: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('skills/authsome/evals/evals.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add skills/authsome/evals/evals.json
git commit -m "feat(evals): rewrite evals.json with new 7-test schema"
```

---

## Task 2: Set up evals/ directory

**Files:**
- Create: `evals/.gitignore`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create evals/.gitignore**

```
tmp/
results/
```

- [ ] **Step 2: Add anthropic to dev dependencies in pyproject.toml**

Find the `[project.optional-dependencies]` dev section in `pyproject.toml` and add `anthropic>=0.40`:

```toml
[project.optional-dependencies]
dev = [
    "anthropic>=0.40",
    # ... existing deps
]
```

- [ ] **Step 3: Install updated deps**

```bash
uv pip install -e ".[dev]"
```

Expected: resolves and installs `anthropic` package.

- [ ] **Step 4: Commit**

```bash
git add evals/.gitignore pyproject.toml uv.lock
git commit -m "chore(evals): add evals directory and anthropic dev dep"
```

---

## Task 3: Implement run_evals.py

**Files:**
- Create: `evals/run_evals.py`

- [ ] **Step 1: Write run_evals.py**

```python
#!/usr/bin/env python3
"""Authsome agentic eval runner.

Runs each eval from skills/authsome/evals/evals.json against the specified
agent CLI, grades the transcript with Claude as LLM judge, and writes
results to evals/results/<timestamp>/grading.json.

Usage:
    uv run python evals/run_evals.py
    uv run python evals/run_evals.py --id 1
"""

import argparse
import json
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).parent.parent
EVALS_JSON = REPO_ROOT / "skills" / "authsome" / "evals" / "evals.json"
SKILL_MD = REPO_ROOT / "skills" / "authsome" / "SKILL.md"
HERMES_SKILL_DIR = Path.home() / ".hermes" / "skills" / "authsome"
CLAUDE_COMMAND_FILE = REPO_ROOT / ".claude" / "commands" / "authsome.md"
TMP_DIR = Path(__file__).parent / "tmp"
RESULTS_DIR = Path(__file__).parent / "results"

JUDGE_SYSTEM_PROMPT = """\
You are an eval grader for an agent called Authsome. You receive:
- An agent transcript (stdout+stderr from a live agent run)
- Environment pre-conditions describing the starting state
- An outcome criterion (did the task succeed?)
- An optional trajectory_efficiency criterion (did the agent take the right number of meaningful steps?)

Return a JSON object with this exact structure:
{
  "outcome": {"passed": true, "evidence": "one sentence quoting or describing transcript evidence"},
  "trajectory_efficiency": {"passed": true, "evidence": "one sentence quoting or describing transcript evidence"}
}

Rules:
- Grade outcome and trajectory_efficiency independently.
- When counting steps for trajectory_efficiency, ignore scaffolding: skill loading,
  reading --help, version checks, and similar overhead. Only task-relevant actions
  count (API calls, auth flows, returning results to the user).
- The actual number of LLM calls will be higher than the expected step count — this is normal.
- If trajectory_efficiency criterion is absent, return {"passed": null, "evidence": "not evaluated"} for it.
- Be strict: burden of proof to pass is on the transcript.
- evidence must quote or specifically reference the transcript, not repeat the criterion.
"""

RATE_LIMIT_SIGNALS = [
    "rate limit",
    "429",
    "too many requests",
    "usage limit",
    "quota exceeded",
]


def load_evals(filter_id: int | None = None) -> list[dict]:
    data = json.loads(EVALS_JSON.read_text())
    evals = data["evals"]
    if filter_id is not None:
        evals = [e for e in evals if e["id"] == filter_id]
        if not evals:
            print(f"[ERROR] No eval with id={filter_id}", file=sys.stderr)
            sys.exit(1)
    return evals


def install_skill_for_agent(agent: str) -> None:
    """Install SKILL.md in the right place for the given agent."""
    if agent == "hermes":
        HERMES_SKILL_DIR.mkdir(parents=True, exist_ok=True)
        dest = HERMES_SKILL_DIR / "SKILL.md"
        shutil.copy2(SKILL_MD, dest)
        print(f"[setup] Copied SKILL.md → {dest}")
    else:
        # claude and codex: install as a slash command in .claude/commands/
        CLAUDE_COMMAND_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILL_MD, CLAUDE_COMMAND_FILE)
        print(f"[setup] Copied SKILL.md → {CLAUDE_COMMAND_FILE}")


def build_command(eval_: dict) -> list[str]:
    agent = eval_.get("agent", "claude")
    prompt = eval_["prompt"]
    if agent == "hermes":
        return ["hermes", "chat", "-q", prompt, "--yolo", "--max-turns", "5", "-v"]
    elif agent == "codex":
        return ["codex", prompt]
    else:
        return ["claude", "-p", prompt]


def run_agent(cmd: list[str]) -> tuple[str, bool]:
    """Run agent command, stream output to terminal, return (transcript, rate_limited)."""
    lines: list[str] = []
    rate_limited = False

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=sys.stdin,
    )

    def stream():
        for raw in proc.stdout:
            line = raw.decode(errors="replace")
            print(line, end="", flush=True)
            lines.append(line)

    t = threading.Thread(target=stream, daemon=True)
    t.start()
    proc.wait()
    t.join()

    transcript = "".join(lines)
    lower = transcript.lower()
    if any(sig in lower for sig in RATE_LIMIT_SIGNALS):
        rate_limited = True

    return transcript, rate_limited


def grade(eval_: dict, transcript: str) -> dict:
    """Call Claude as LLM judge and return grading result dict."""
    client = anthropic.Anthropic()

    has_trajectory = "trajectory_efficiency" in eval_

    user_content = f"""Environment: {eval_["environment"]}

Outcome criterion: {eval_["outcome"]}

Trajectory efficiency criterion: {eval_.get("trajectory_efficiency", "(not provided — skip this grade)")}

Transcript:
---
{transcript[-12000:]}
---
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    verdict = json.loads(raw)

    if not has_trajectory:
        verdict["trajectory_efficiency"] = {"passed": None, "evidence": "not evaluated"}

    return verdict


def save_grading(results: list[dict], run_dir: Path) -> Path:
    passed = sum(1 for r in results if r.get("status") != "skipped" and r["outcome"]["passed"])
    failed = sum(1 for r in results if r.get("status") != "skipped" and not r["outcome"]["passed"])
    skipped = sum(1 for r in results if r.get("status") == "skipped")

    grading = {
        "skill_name": "authsome",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": len(results),
        },
        "results": results,
    }
    out = run_dir / "grading.json"
    out.write_text(json.dumps(grading, indent=2))
    return out


def print_env_banner(eval_: dict) -> None:
    print()
    print("=" * 60)
    print(f"EVAL {eval_['id']}: {eval_.get('name', eval_['prompt'])}")
    print(f"Agent   : {eval_.get('agent', 'claude')}")
    print(f"Environ : {eval_['environment']}")
    if eval_.get("requires_human"):
        print()
        print("HUMAN ACTION REQUIRED:")
        print(f"  {eval_['human_instructions']}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run authsome agentic evals")
    parser.add_argument("--id", type=int, default=None, help="Run only eval with this id")
    args = parser.parse_args()

    evals = load_evals(args.id)

    # Install skill once per unique agent type
    agents_seen: set[str] = set()
    for eval_ in evals:
        agent = eval_.get("agent", "claude")
        if agent not in agents_seen:
            install_skill_for_agent(agent)
            agents_seen.add(agent)

    run_dir = RESULTS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for eval_ in evals:
        print_env_banner(eval_)

        if eval_.get("requires_human"):
            input("Press Enter when pre-conditions are met and you are ready to start...")

        cmd = build_command(eval_)
        print(f"[run] {' '.join(cmd)}")

        transcript, rate_limited = run_agent(cmd)

        transcript_file = run_dir / f"transcript_{eval_['id']}.txt"
        transcript_file.write_text(transcript)

        if rate_limited:
            print(f"\n[SKIPPED] Eval {eval_['id']} — rate limit hit. Switch model and retry.")
            results.append({
                "id": eval_["id"],
                "name": eval_.get("name", ""),
                "prompt": eval_["prompt"],
                "agent": eval_.get("agent", "claude"),
                "environment": eval_["environment"],
                "requires_human": eval_.get("requires_human", False),
                "status": "skipped",
                "outcome": {"passed": None, "evidence": "Rate limit hit"},
                "trajectory_efficiency": {"passed": None, "evidence": "Rate limit hit"},
            })
            continue

        print(f"\n[grading] Calling LLM judge for eval {eval_['id']}...")
        verdict = grade(eval_, transcript)

        outcome_icon = "✓" if verdict["outcome"]["passed"] else "✗"
        traj_icon = (
            "✓" if verdict["trajectory_efficiency"]["passed"]
            else ("—" if verdict["trajectory_efficiency"]["passed"] is None else "✗")
        )
        print(f"[result] outcome={outcome_icon}  trajectory={traj_icon}")
        print(f"         outcome  : {verdict['outcome']['evidence']}")
        print(f"         trajectory: {verdict['trajectory_efficiency']['evidence']}")

        results.append({
            "id": eval_["id"],
            "name": eval_.get("name", ""),
            "prompt": eval_["prompt"],
            "agent": eval_.get("agent", "claude"),
            "environment": eval_["environment"],
            "requires_human": eval_.get("requires_human", False),
            **verdict,
        })

    grading_path = save_grading(results, run_dir)
    summary = json.loads(grading_path.read_text())["summary"]
    print()
    print(f"Done: {summary['passed']} passed / {summary['failed']} failed / {summary['skipped']} skipped out of {summary['total']}")
    print(f"Results: {grading_path}")
    print(f"\nTo view report: uv run python evals/generate_report.py {grading_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test imports**

```bash
uv run python -c "import evals.run_evals" 2>&1 || uv run python evals/run_evals.py --help
```

Expected: help text printed, no import errors.

- [ ] **Step 3: Commit**

```bash
git add evals/run_evals.py
git commit -m "feat(evals): add run_evals.py — agent runner and LLM judge"
```

---

## Task 4: Implement generate_report.py

**Files:**
- Create: `evals/generate_report.py`

- [ ] **Step 1: Write generate_report.py**

```python
#!/usr/bin/env python3
"""Generate an HTML report from a grading.json produced by run_evals.py.

Usage:
    uv run python evals/generate_report.py evals/results/<timestamp>/grading.json
"""

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path


def verdict_icon(passed: bool | None) -> tuple[str, str]:
    """Return (icon, css_class) for a passed value."""
    if passed is True:
        return "✓", "pass"
    if passed is False:
        return "✗", "fail"
    return "—", "skip"


def generate_html(data: dict) -> str:
    summary = data["summary"]
    results = data["results"]
    skill_name = data.get("skill_name", "authsome")
    timestamp = data.get("timestamp", "")

    parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(skill_name)} — Eval Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Lora:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #faf9f5;
      --surface: #ffffff;
      --border: #e8e6dc;
      --text: #141413;
      --text-muted: #b0aea5;
      --header-bg: #141413;
      --header-text: #faf9f5;
      --green: #788c5d;
      --green-bg: #eef2e8;
      --red: #c44;
      --red-bg: #fceaea;
      --radius: 6px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Lora', Georgia, serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}
    .header {{
      background: var(--header-bg);
      color: var(--header-text);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .header h1 {{ font-family: 'Poppins', sans-serif; font-size: 1.25rem; font-weight: 600; }}
    .header .meta {{ font-size: 0.8rem; opacity: 0.7; text-align: right; }}
    .summary-bar {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 0.75rem 2rem;
      font-family: 'Poppins', sans-serif;
      font-size: 0.875rem;
      display: flex;
      gap: 1.5rem;
    }}
    .summary-bar .chip {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      font-weight: 600;
    }}
    .chip-pass {{ background: var(--green-bg); color: var(--green); }}
    .chip-fail {{ background: var(--red-bg); color: var(--red); }}
    .chip-skip {{ background: #f5f5f0; color: var(--text-muted); }}
    .main {{ padding: 1.5rem 2rem; display: flex; flex-direction: column; gap: 1rem; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }}
    .card-header {{
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      font-family: 'Poppins', sans-serif;
      font-size: 0.875rem;
    }}
    .eval-id {{
      font-size: 0.75rem;
      color: var(--text-muted);
      min-width: 2rem;
    }}
    .eval-name {{ font-weight: 600; flex: 1; }}
    .agent-badge {{
      font-size: 0.7rem;
      padding: 0.15rem 0.5rem;
      border-radius: 3px;
      background: #f0f0e8;
      color: var(--text-muted);
      font-family: monospace;
    }}
    .human-badge {{
      font-size: 0.7rem;
      padding: 0.15rem 0.5rem;
      border-radius: 3px;
      background: #fff3e0;
      color: #b45309;
    }}
    .verdict-icons {{ display: flex; gap: 0.5rem; }}
    .verdict-block {{
      display: flex;
      align-items: center;
      gap: 0.3rem;
      font-size: 0.8rem;
    }}
    .verdict-label {{ color: var(--text-muted); font-size: 0.7rem; }}
    .icon {{ font-size: 1.1rem; font-weight: bold; }}
    .pass {{ color: var(--green); }}
    .fail {{ color: var(--red); }}
    .skip {{ color: var(--text-muted); }}
    .card-body {{ padding: 0.75rem 1rem; font-size: 0.875rem; display: flex; flex-direction: column; gap: 0.5rem; }}
    .field-row {{ display: flex; gap: 0.5rem; }}
    .field-label {{ color: var(--text-muted); font-size: 0.75rem; min-width: 6rem; padding-top: 0.1rem; }}
    .field-value {{ flex: 1; line-height: 1.5; }}
    .evidence {{ font-style: italic; color: #555; }}
    details summary {{ cursor: pointer; color: var(--text-muted); font-size: 0.8rem; }}
    details[open] summary {{ margin-bottom: 0.4rem; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>{html.escape(skill_name)} — Eval Report</h1>
    </div>
    <div class="meta">{html.escape(timestamp)}</div>
  </div>
  <div class="summary-bar">
    <span>Results:</span>
    <span class="chip chip-pass">✓ {summary['passed']} passed</span>
    <span class="chip chip-fail">✗ {summary['failed']} failed</span>
    <span class="chip chip-skip">— {summary['skipped']} skipped</span>
    <span style="color:var(--text-muted)">of {summary['total']} total</span>
  </div>
  <div class="main">
"""]

    for r in results:
        outcome = r.get("outcome", {})
        traj = r.get("trajectory_efficiency", {})
        o_icon, o_cls = verdict_icon(outcome.get("passed"))
        t_icon, t_cls = verdict_icon(traj.get("passed"))
        is_skipped = r.get("status") == "skipped"
        human = r.get("requires_human", False)

        parts.append(f"""    <div class="card">
      <div class="card-header">
        <span class="eval-id">#{r['id']}</span>
        <span class="eval-name">{html.escape(r.get('name', r['prompt']))}</span>
        <span class="agent-badge">{html.escape(r.get('agent', 'claude'))}</span>
        {"<span class='human-badge'>human</span>" if human else ""}
        <div class="verdict-icons">
          <div class="verdict-block">
            <span class="verdict-label">outcome</span>
            <span class="icon {o_cls}">{o_icon}</span>
          </div>
          <div class="verdict-block">
            <span class="verdict-label">trajectory</span>
            <span class="icon {t_cls}">{t_icon}</span>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="field-row">
          <span class="field-label">prompt</span>
          <span class="field-value">{html.escape(r['prompt'])}</span>
        </div>
        <details>
          <summary>environment</summary>
          <div class="field-row">
            <span class="field-value">{html.escape(r.get('environment', ''))}</span>
          </div>
        </details>
        {"<div class='field-row'><span class='field-label'>skipped</span><span class='field-value evidence'>Rate limit hit — switch model and retry</span></div>" if is_skipped else f"""
        <div class="field-row">
          <span class="field-label">outcome</span>
          <span class="field-value evidence">{html.escape(outcome.get('evidence', ''))}</span>
        </div>
        <div class="field-row">
          <span class="field-label">trajectory</span>
          <span class="field-value evidence">{html.escape(traj.get('evidence', ''))}</span>
        </div>"""}
      </div>
    </div>
""")

    parts.append("""  </div>
</body>
</html>""")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML report from grading.json")
    parser.add_argument("grading_json", help="Path to grading.json")
    parser.add_argument("-o", "--output", default=None, help="Output HTML path (default: report.html next to grading.json)")
    args = parser.parse_args()

    grading_path = Path(args.grading_json)
    data = json.loads(grading_path.read_text())

    html_out = Path(args.output) if args.output else grading_path.parent / "report.html"
    html_out.write_text(generate_html(data))
    print(f"Report written to {html_out}")

    # Open in default browser
    subprocess.run(["open", str(html_out)], check=False)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add evals/generate_report.py
git commit -m "feat(evals): add generate_report.py — HTML eval report generator"
```

---

## Task 5: Smoke-test with Eval 1

**Goal:** Verify the full pipeline works end-to-end for the hermes Skill Triggering eval before running the full suite.

- [ ] **Step 1: Run eval 1 only**

```bash
uv run python evals/run_evals.py --id 1
```

Watch for:
- `[setup] Copied SKILL.md → ~/.hermes/skills/authsome/SKILL.md`
- hermes verbose output streaming to terminal
- `[grading]` line after hermes completes
- `[result] outcome=✓` (or `✗` if skill did not trigger — this is a real signal)
- `Results: evals/results/<timestamp>/grading.json`

- [ ] **Step 2: Generate and open the report**

```bash
uv run python evals/generate_report.py evals/results/$(ls -t evals/results | head -1)/grading.json
```

Expected: browser opens with a one-card HTML report showing the outcome and trajectory verdicts.

- [ ] **Step 3: Confirm grading.json is well-formed**

```bash
python3 -c "
import json
from pathlib import Path
p = sorted(Path('evals/results').iterdir())[-1] / 'grading.json'
d = json.loads(p.read_text())
print('summary:', d['summary'])
print('outcome passed:', d['results'][0]['outcome']['passed'])
"
```

Expected: prints summary dict and a boolean `passed` value.

- [ ] **Step 4: Commit final state**

```bash
git add evals/
git commit -m "feat(evals): complete eval runner pipeline, smoke-tested with eval 1"
```

---

## Self-Review

**Spec coverage:**
- ✓ evals.json schema (id, name, prompt, agent, environment, outcome, trajectory_efficiency optional, requires_human, human_instructions) — Task 1
- ✓ hermes global install / claude local install — Task 3 (`install_skill_for_agent`)
- ✓ hermes command with `-v` flag — Task 3 (`build_command`)
- ✓ Rate limit detection → skipped — Task 3 (`RATE_LIMIT_SIGNALS`)
- ✓ Human-in-the-loop pause with `Press Enter` — Task 3 (`print_env_banner` + `input()`)
- ✓ Transcript streamed to terminal and captured — Task 3 (`run_agent` with threading)
- ✓ LLM judge with two independent verdicts — Task 3 (`grade`)
- ✓ trajectory_efficiency optional (null when absent) — Task 3 (`grade`)
- ✓ grading.json format — Task 3 (`save_grading`)
- ✓ HTML report matching skill-creator style — Task 4 (`generate_report.py`)
- ✓ `--id` flag for single eval — Task 3 (`main`)
- ✓ `evals/tmp/` and `evals/results/` gitignored — Task 2

**Placeholder scan:** None found.

**Type consistency:** `passed: bool | None` used consistently across `grade()`, `save_grading()`, `verdict_icon()`, and the HTML template.

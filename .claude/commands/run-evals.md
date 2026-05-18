# Run Authsome Evals

Interactive eval runner for the authsome skill. You orchestrate everything
inline — agent invocation, transcript parsing, grading, and result saving.
There is no separate Python runner script.

## Pre-session setup

Run this once before starting an eval session.

**1. Install the latest authsome CLI:**

```bash
uv sync
```

Verify:

```bash
uv run authsome --version
```

**2. Create a fresh identity and verify the existing one still works:**

```bash
# Check the current identity is healthy
uv run authsome doctor

# Create a new identity for the eval session
uv run authsome profile create --json
```

Save the new `profile` handle. Then switch to it:

```bash
uv run authsome profile use <new-handle>
```

**3. Confirm the new identity starts clean:**

```bash
uv run authsome list
```

Expected: no providers connected. If any show `connected`, the wrong
profile may be active — check with `cat ~/.authsome/client/config.json`.

**4. Restart the daemon using the dev version:**

The daemon may be running as a globally tool-installed binary while the CLI runs via `uv run`. This version mismatch causes PoP auth failures (spurious 401s) that confuse agents into running `authsome init` mid-eval, corrupting the eval profile. Restart to ensure both CLI and daemon use the same code:

```bash
uv run authsome daemon restart
```

Verify:

```bash
uv run authsome list
```

Expected: the same clean state as before. If the daemon fails to restart, check for port conflicts with `lsof -i :7998`.

**5. Remove hermes GitHub skills to avoid interference with authsome triggering:**

```bash
rm -rf ~/.hermes/skills/github
```

This prevents hermes from using its bundled GitHub skills instead of loading authsome.

**6. Verify hermes and claude are working:**

```bash
hermes chat -Q -q "reply with the single word OK" -t ""
claude -p "reply with the single word OK" --output-format text
```

Expected: both respond with `OK`. Hermes runs the eval agents; claude is the LLM judge.

---

## Arguments

- No args — run all non-optional evals (ids 1–6)
- `--id N` — run only eval with that id
- `--all` — include optional evals (currently id 7: Agentic Installation)

---

## Steps

### 1. Load evals

Read `evals/evals.json`. Show the user a table of which
evals will run (id, name, agent, requires_human, optional).

Read `~/.authsome/client/config.json` and save `active_identity` as
`EVAL_HANDLE` — this is the fresh profile created during pre-session setup.

Create the run directory and save as `RUN_DIR`:

```bash
mkdir -p "evals/results/$(date +%Y%m%d_%H%M%S)"
```

---

### 2. Per-eval loop

For each eval to run, **in order**:

#### a. State-check

Run `uv run authsome list` and **show the full output to the user**.
Compare it against the eval's `environment` field and explicitly state
whether it matches. If it matches, proceed. If not, show the mismatch
and fix it inline using `uv run authsome` commands (e.g.
`uv run authsome logout github`). Re-check until state matches.

If the required state cannot be reached automatically (e.g. gh CLI login
requires interactive browser auth that isn't part of the eval), ask the
user whether to skip. If they say skip, write a null verdict and record
it in grading.json, then move to the next eval:

```bash
# Write null verdict
cat > RUN_DIR/verdict_N.json <<'EOF'
{
  "outcome": {"passed": null, "evidence": "skipped by user"},
  "trajectory_efficiency": {"passed": null, "evidence": "skipped by user"}
}
EOF

# Capture authsome state
uv run authsome list > RUN_DIR/authsome_state_N.txt 2>&1

# Append to grading.json (same save script as step f, RATE_LIMITED=false)
```

Then run the step-f save script for this eval and continue to the next one.

For `requires_human` evals, also show `human_instructions` now.

#### b. Install the skill for the agent

```bash
# For hermes evals
mkdir -p ~/.hermes/skills/authsome
cp skills/authsome/SKILL.md ~/.hermes/skills/authsome/SKILL.md

# For claude evals
cp skills/authsome/SKILL.md .claude/commands/authsome.md
```

#### c. Run the agent

Before running the agent, read `max_turns` from the eval object (default
`12` if absent) and store it as `MAX_TURNS`.

**Hermes evals:**

```bash
hermes chat -q "PROMPT" --yolo --max-turns MAX_TURNS \
  2>&1 | tee RUN_DIR/transcript_N.txt
```

The combined stdout+stderr is the transcript. Save `RATE_LIMITED=false`
unless the output contains: `rate limit`, `429`, `too many requests`,
`usage limit`, or `quota exceeded`.

**Claude evals — turn 1:**

```bash
claude --dangerously-skip-permissions --verbose --output-format stream-json \
  --max-turns MAX_TURNS -p "PROMPT" > RUN_DIR/raw_N_t1.jsonl 2>&1
```

Then parse the raw stream-json, extract the human-readable transcript,
and detect whether the agent is waiting for a human action:

```bash
uv run python - RUN_DIR/raw_N_t1.jsonl > RUN_DIR/transcript_N.txt 2> RUN_DIR/meta_N.txt <<'PYEOF'
import sys, json, re

RATE_LIMIT_SIGNALS = ["rate limit", "429", "too many requests", "usage limit", "quota exceeded"]
path = sys.argv[1]
lines_out = []
session_id = None

for line in open(path):
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        lines_out.append(line)
        continue
    t = ev.get("type", "")
    if t == "assistant" and "message" in ev:
        for block in ev["message"].get("content", []):
            if block.get("type") == "text":
                lines_out.append(f"[assistant] {block['text']}")
            elif block.get("type") == "tool_use":
                inp = json.dumps(block.get("input", {}))
                lines_out.append(f"[tool_use] {block['name']}({inp})")
    elif t == "user" and "message" in ev:
        for block in ev["message"].get("content", []):
            if block.get("type") == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                lines_out.append(f"[tool_result] {str(content)[:800]}")
    elif t == "result":
        if ev.get("result"):
            lines_out.append(f"[result] {ev['result']}")
        if ev.get("error"):
            lines_out.append(f"[error] {ev['error']}")
        if ev.get("session_id"):
            session_id = ev["session_id"]

transcript = "\n".join(lines_out)
print(transcript)

# Emit metadata to stderr for the caller to read
url_match = re.search(r'http://127\.0\.0\.1:\d+/\S+', transcript)
if url_match:
    print(f"WAITING_URL={url_match.group()}", file=sys.stderr)
if session_id:
    print(f"SESSION_ID={session_id}", file=sys.stderr)
rate_limited = any(sig in transcript.lower() for sig in RATE_LIMIT_SIGNALS)
print(f"RATE_LIMITED={'true' if rate_limited else 'false'}", file=sys.stderr)
PYEOF
```

Read `RUN_DIR/meta_N.txt` and extract:

```bash
SESSION_ID=$(grep "^SESSION_ID=" RUN_DIR/meta_N.txt | cut -d= -f2)
WAITING_URL=$(grep "^WAITING_URL=" RUN_DIR/meta_N.txt | cut -d= -f2)
RATE_LIMITED=$(grep "^RATE_LIMITED=" RUN_DIR/meta_N.txt | cut -d= -f2)
```

#### d. Human handoff (requires_human evals only)

**Case 1 — Agent-initiated interrupt (`expected_interrupt` is set):**

If the eval has an `expected_interrupt` field, read `RUN_DIR/transcript_N.txt` and judge
whether the agent's final message matches the described interrupt — i.e. the agent paused
mid-task to ask the user a clarifying question or request input instead of proceeding
autonomously. If it matches, auto-resume without human input by sending `next_turn_instruction`
back to the session:

```bash
claude --resume SESSION_ID \
  --dangerously-skip-permissions --verbose --output-format stream-json \
  --max-turns MAX_TURNS -p "NEXT_TURN_INSTRUCTION" > RUN_DIR/raw_N_t2.jsonl 2>&1
```

Parse the continuation with the same parse script (substitute `raw_N_t2.jsonl` and
`meta_N_t2.txt`) and append to `RUN_DIR/transcript_N.txt`. Update `RATE_LIMITED` from
`meta_N_t2.txt`. Then continue to step e for grading — do not prompt the human unless
`WAITING_URL` is non-empty in the resumed turn.

**Case 2 — Browser auth flow (`WAITING_URL` is non-empty):**

If `WAITING_URL` is non-empty, the agent started an auth flow and is
suspended at its session boundary. Show the user:

> The agent is waiting. Please complete the auth flow at: `WAITING_URL`
> Tell me "done" when finished.

Wait for the user to reply "done". Then resume the claude session and
append the continuation to the transcript:

```bash
claude --resume SESSION_ID \
  --dangerously-skip-permissions --verbose --output-format stream-json \
  --max-turns MAX_TURNS -p "done" > RUN_DIR/raw_N_t2.jsonl 2>&1
```

Parse turn 2 with the same script above (substitute `raw_N_t2.jsonl` and
`meta_N_t2.txt`), then append its transcript to `RUN_DIR/transcript_N.txt`:

```bash
uv run python - RUN_DIR/raw_N_t2.jsonl >> RUN_DIR/transcript_N.txt 2> RUN_DIR/meta_N_t2.txt <<'PYEOF'
# ... same parse script as above ...
PYEOF

# Update RATE_LIMITED if turn 2 was rate-limited
RATE_LIMITED_T2=$(grep "^RATE_LIMITED=" RUN_DIR/meta_N_t2.txt | cut -d= -f2)
[ "$RATE_LIMITED_T2" = "true" ] && RATE_LIMITED=true
```

If `WAITING_URL` is empty and no agent-initiated interrupt was detected for a `requires_human`
eval, the agent finished in one turn (e.g. it polled for completion itself) — no resume needed.

#### e. Grade the transcript

Call claude as the LLM judge with the full eval criteria and the transcript:

```bash
uv run python - RUN_DIR/transcript_N.txt EVAL_ID <<'PYEOF' > RUN_DIR/verdict_N.json
import sys, json, subprocess
from pathlib import Path

transcript = Path(sys.argv[1]).read_text()
eval_id = int(sys.argv[2])
evals = json.loads(Path("evals/evals.json").read_text())["evals"]
eval_ = next(e for e in evals if e["id"] == eval_id)

JUDGE_PROMPT = """\
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
- evidence must quote or specifically reference the transcript, not repeat the criterion.\
"""

prompt = f"""{JUDGE_PROMPT}

Environment: {eval_["environment"]}

Outcome criterion: {eval_["outcome"]}

Trajectory efficiency criterion: {eval_.get("trajectory_efficiency", "(not provided — skip this grade)")}

Full transcript:
---
{transcript}
---

Return ONLY valid JSON, no markdown fences."""

result = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "text"],
    capture_output=True, text=True, timeout=120,
)

if result.returncode != 0:
    raise RuntimeError(f"claude judge failed (exit {result.returncode}): {result.stderr[:300]}")

raw = result.stdout.strip()
if "```" in raw:
    for part in raw.split("```"):
        part = part.strip().lstrip("json").strip()
        if part.startswith("{"):
            raw = part
            break

verdict = json.loads(raw)
if "trajectory_efficiency" not in eval_:
    verdict["trajectory_efficiency"] = {"passed": None, "evidence": "not evaluated"}

print(json.dumps(verdict, indent=2))
PYEOF
```

Read `RUN_DIR/verdict_N.json` and print the result line:

```
[result] outcome=✓/✗  trajectory=✓/✗/—
         outcome  : <evidence>
         trajectory: <evidence>
```

#### f. Append result to grading.json

```bash
uv run python - RUN_DIR/grading.json EVAL_ID "$RATE_LIMITED" <<'PYEOF'
import sys, json
from datetime import datetime
from pathlib import Path

grading_path = Path(sys.argv[1])
eval_id = int(sys.argv[2])
rate_limited = sys.argv[3] == "true"

evals = json.loads(Path("evals/evals.json").read_text())["evals"]
eval_ = next(e for e in evals if e["id"] == eval_id)

run_dir = grading_path.parent
verdict = json.loads((run_dir / f"verdict_{eval_id}.json").read_text())
authsome_state = (run_dir / f"authsome_state_{eval_id}.txt").read_text() \
    if (run_dir / f"authsome_state_{eval_id}.txt").exists() else ""

result_entry = {
    "id": eval_id,
    "name": eval_.get("name", ""),
    "prompt": eval_["prompt"],
    "agent": eval_.get("agent", "claude"),
    "environment": eval_["environment"],
    "authsome_state": authsome_state,
    "requires_human": eval_.get("requires_human", False),
    "rate_limited": rate_limited,
    **verdict,
}

existing = {"results": []}
if grading_path.exists():
    existing = json.loads(grading_path.read_text())

all_results = existing["results"] + [result_entry]
passed  = sum(1 for r in all_results if r["outcome"]["passed"] is True)
failed  = sum(1 for r in all_results if r["outcome"]["passed"] is False)
skipped = sum(1 for r in all_results if r["outcome"]["passed"] is None)

grading = {
    "skill_name": "authsome",
    "timestamp": datetime.now().isoformat(timespec="seconds"),
    "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(all_results)},
    "results": all_results,
}
grading_path.write_text(json.dumps(grading, indent=2))

summary = grading["summary"]
print(f"Done: {summary['passed']} passed / {summary['failed']} failed / {summary['skipped']} skipped out of {summary['total']}")
print(f"Results: {grading_path}")
PYEOF
```

Before running the save script, write the current authsome state to
`RUN_DIR/authsome_state_N.txt` so it's captured in the grading record:

```bash
uv run authsome list > RUN_DIR/authsome_state_N.txt 2>&1
```

#### g. State-check and continue

After showing the verdict, immediately prepare for the next eval:

1. Run `uv run authsome list` and compare against the next eval's `environment` field.
2. Fix any mismatches inline (e.g. `uv run authsome logout github`). Re-check until state matches.
3. Only pause and ask the user when:
   - An OAuth login requires a browser flow (show the URL, wait for "done")
   - A `requires_human` eval where the user must act during the run

---

### 3. Teardown

Delete the eval profile's key files:

```bash
rm ~/.authsome/client/identities/EVAL_HANDLE.json
rm ~/.authsome/client/identities/EVAL_HANDLE.key
```

Then switch back to the user's original profile:

```bash
uv run authsome profile use <original-handle>
```

---

### 4. Generate report

```bash
uv run python evals/generate_report.py RUN_DIR/grading.json
```

Tell the user the report path. The script opens it automatically.

# Run Authsome Evals

Interactive eval runner for the authsome skill. You orchestrate the
state-check conversation; the Python script handles agent execution and
grading.

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

**4. Remove hermes GitHub skills to avoid interference with authsome triggering:**

```bash
rm -rf ~/.hermes/skills/github
```

This prevents hermes from using its bundled GitHub skills instead of loading authsome.

**5. Verify hermes is working:**

```bash
hermes chat -Q -q "reply with the single word OK" -t ""
```

Expected: response contains `OK`. If it fails, check your hermes config
before running evals (hermes is used as the LLM judge).

---

## Arguments

- No args — run all non-optional evals (ids 1–6)
- `--id N` — run only eval with that id
- `--all` — include optional evals (currently id 7: Agentic Installation)

## Steps

### 1. Load evals

Read `skills/authsome/evals/evals.json`. Show the user a table of which
evals will run (id, name, agent, requires_human, optional).

Read `~/.authsome/client/config.json` and save `active_identity` as
`EVAL_HANDLE` — this is the fresh profile created during pre-session setup.

Create the run directory and save as `RUN_DIR`:

```bash
mkdir -p "evals/results/$(date +%Y%m%d_%H%M%S)"
```

### 2. Per-eval loop

For each eval to run, **in order**:

**a. State-check**

Run `uv run authsome list` and **show the full output to the user**.
Compare it against the eval's `environment` field and explicitly state
whether it matches. If it matches, proceed. If not, show the mismatch
and wait for the user to fix it (same loop as step c). For
`requires_human` evals, also show `human_instructions` now so the user
knows what to expect during the run.

**b. Run the eval**

Run via the script for all agent types:

```bash
uv run python evals/run_evals.py --id N --profile EVAL_HANDLE --run-dir RUN_DIR
```

The script invokes the correct agent (`hermes` or `claude --verbose`) as a
subprocess, captures its full stdout/stderr as the transcript, grades it with
the LLM judge, and appends results to `RUN_DIR/grading.json`.

The script prints a `[result]` line at the end —
show the outcome and trajectory icons to the user as a brief verdict.

**c. State-check and continue**

After showing the verdict, immediately prepare for the next eval without
asking the user:

1. Run `uv run authsome list` and compare against the next eval's
   `environment` field.

2. Fix any mismatches inline using `uv run authsome` commands (e.g.
   `uv run authsome logout github`). Re-check until state matches.

3. Only pause and ask the user when you need their help — for example:
   - An OAuth login that requires completing a browser flow
   - A credential (API key, password) that only the user knows
   - A `requires_human` eval where the user must act during the run
   In those cases, explain what you need and wait for confirmation before
   proceeding.

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

### 4. Generate report

```bash
uv run python evals/generate_report.py RUN_DIR/grading.json
```

Tell the user the report path. The script opens it automatically.

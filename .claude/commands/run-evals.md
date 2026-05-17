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

**a. Check current authsome state**

```bash
uv run authsome list
```

Show the output to the user. Also show the eval's `environment` field
(the expected pre-conditions). Ask:

> "The expected state is: [environment]. Does the current state match?
> If you need to add or remove credentials, do it in another terminal
> and let me know when you're ready."

Wait for the user to confirm before proceeding. This is the natural
place for the user to fix state without any hardcoded pauses.

For evals with `"requires_human": true`, also show the
`human_instructions` at this point, since the user will need to act
during the agent run (e.g. complete an OAuth flow in the browser).

**b. Run the eval**

```bash
uv run python evals/run_evals.py --id N --profile EVAL_HANDLE --run-dir RUN_DIR
```

Stream the output. The script prints a `[result]` line at the end —
show the outcome and trajectory icons to the user as a brief verdict.

**c. Confirm before next eval**

After showing the verdict, ask if the user is ready to continue to the
next eval (or stop here).

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

# Agentic Eval Runner — Implementation Summary

**Status:** Implemented (2026-05-17)

This document summarises what was built and the key decisions made during implementation. For the current design, see the [design spec](../specs/2026-05-17-agentic-eval-runner-design.md).

---

## What was built

| File | Purpose |
|---|---|
| `skills/authsome/evals/evals.json` | 7 eval definitions in execution order |
| `evals/run_evals.py` | Non-interactive runner: install skill, run agent, grade, save |
| `evals/generate_report.py` | Reads grading.json, renders HTML report, opens browser |
| `.claude/commands/run-evals.md` | `/run-evals` slash command — orchestrates the interactive flow |
| `evals/.gitignore` | Ignores `tmp/` and `results/` |

`evals/setup.md` was created then merged into `run-evals.md` and deleted.

---

## Key decisions made during implementation

**LLM judge: hermes instead of Claude API**
Originally planned to use the `anthropic` SDK (Haiku). Switched to `hermes chat -Q -q ... -t ""` because `claude -p` stopped working for subprocess use (billing change). The `anthropic` dev dependency was added then removed. Hermes is already required for eval 1, so this adds no new dependency.

**Profile isolation instead of wiping state**
Original plan: `rm -rf ~/.authsome` + `authsome init`. Changed to `authsome profile create` + `profile use` so the user's real credentials are preserved. At session end, the eval profile's `.json` and `.key` files are deleted from `~/.authsome/client/identities/`.

**Non-interactive runner + `/run-evals` command**
Originally `run_evals.py` had `input()` prompts. Moved all interaction into the `/run-evals` Claude command so the user can check and fix authsome state conversationally in the same terminal. The script gained `--profile` and `--run-dir` flags for single-eval calls from the command; `save_grading` gained an `append` mode to accumulate results across those calls.

**Rate limits: warn and grade, don't skip**
Original plan skipped evals on rate limit and marked them `status: skipped`. Changed to: emit `[WARNING]`, grade the partial transcript anyway (the hermes judge can still evaluate partial evidence), and record `rate_limited: true` in the result.

**Eval 7 (Agentic Installation) moved to last and made optional**
Originally eval 2. Moved to id 7 with `"optional": true` because it requires uninstalling authsome, which destroys the eval profile's stored credentials and would break subsequent scenario tests.

**authsome_state captured per eval**
`authsome list` output is captured before each eval and stored as `authsome_state` in the result record. Rendered as a collapsible section in the HTML report so the grader can see exactly what state each test started from.

---

## evals.json sequence rationale

| ID | State dependency |
|---|---|
| 1 | No credentials needed — just checks skill triggering in hermes |
| 2 | Starts clean; connects GitHub → state carries to test 3 |
| 3 | Consumes GitHub connection from test 2 |
| 4 | GitHub disconnected (run `authsome logout github` before); uses gh CLI instead |
| 5 | No authsome credentials needed; uses firecrawl API key flow |
| 6 | No authsome credentials needed; uses ClickUp OAuth flow |
| 7 | Optional; uninstalls authsome CLI — must run last |

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

REPO_ROOT = Path(__file__).parent.parent
EVALS_JSON = REPO_ROOT / "skills" / "authsome" / "evals" / "evals.json"
SKILL_MD = REPO_ROOT / "skills" / "authsome" / "SKILL.md"
HERMES_SKILL_DIR = Path.home() / ".hermes" / "skills" / "authsome"
CLAUDE_COMMAND_FILE = REPO_ROOT / ".claude" / "commands" / "authsome.md"
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
    rate_limited = any(sig in transcript.lower() for sig in RATE_LIMIT_SIGNALS)

    return transcript, rate_limited


def grade(eval_: dict, transcript: str) -> dict:
    """Call Claude as LLM judge via `claude -p` and return grading result dict."""
    has_trajectory = "trajectory_efficiency" in eval_

    user_content = f"""Environment: {eval_["environment"]}

Outcome criterion: {eval_["outcome"]}

Trajectory efficiency criterion: {eval_.get("trajectory_efficiency", "(not provided — skip this grade)")}

Transcript (last 4000 chars):
---
{transcript[-4000:]}
---

Return ONLY valid JSON, no markdown fences."""

    result = subprocess.run(
        ["claude", "--system-prompt", JUDGE_SYSTEM_PROMPT, "-p", user_content],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude -p judge failed (exit {result.returncode}): {result.stderr[:300]}")

    raw = result.stdout.strip()
    # Strip markdown fences if present
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            if part.startswith("{"):
                raw = part
                break

    verdict = json.loads(raw)

    if not has_trajectory:
        verdict["trajectory_efficiency"] = {"passed": None, "evidence": "not evaluated"}

    return verdict


def save_grading(results: list[dict], run_dir: Path) -> Path:
    passed = sum(1 for r in results if r["outcome"]["passed"] is True)
    failed = sum(1 for r in results if r["outcome"]["passed"] is False)
    skipped = sum(1 for r in results if r["outcome"]["passed"] is None)

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
            print(f"\n[WARNING] Eval {eval_['id']} — agent hit rate limit. Grading partial transcript anyway.")

        print(f"\n[grading] Calling LLM judge for eval {eval_['id']}...")
        verdict = grade(eval_, transcript)

        outcome_icon = "✓" if verdict["outcome"]["passed"] else "✗"
        traj_passed = verdict["trajectory_efficiency"]["passed"]
        traj_icon = "✓" if traj_passed is True else ("—" if traj_passed is None else "✗")
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
            "rate_limited": rate_limited,
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

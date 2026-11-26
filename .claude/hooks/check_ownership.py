#!/usr/bin/env python3
"""Claude Code PreToolUse hook: ask before editing a file that belongs to another teammate.

Reads OWNERS (repo root). Works out who "you" are from:
  1. the VSEARCH_OWNER env var (set it in .claude/settings.local.json, see CLAUDE.md), else
  2. a first-name match in `git config user.name` (e.g. "Tanay Raj" -> tanay).

Your own files and unlisted files: no output, normal permission flow.
Someone else's file or a shared contract file: Claude must ask you first, with the reason.
Standard library only, so it runs with any python3.
"""
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

TEAM = ("tanay", "aditya", "darshil")


def repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env).resolve() if env else Path(__file__).resolve().parents[2]


def load_rules(root: Path) -> list[tuple[str, str]]:
    f = root / "OWNERS"
    if not f.exists():
        return []
    rules = []
    for line in f.read_text().splitlines():
        parts = line.split("#", 1)[0].split()
        if len(parts) == 2:
            rules.append((parts[0], parts[1].lower()))
    return rules


def owner_of(rel: str, rules) -> str | None:
    owner = None
    for pattern, who in rules:  # last match wins
        hit = rel.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatch(rel, pattern)
        if hit:
            owner = who
    return owner


def whoami(root: Path) -> str | None:
    me = os.environ.get("VSEARCH_OWNER", "").strip().lower()
    if me:
        return me
    try:
        name = subprocess.run(["git", "-C", str(root), "config", "user.name"],
                              capture_output=True, text=True, timeout=5).stdout.lower().split()
    except Exception:
        return None
    return next((m for m in TEAM if m in name), None)


def main() -> int:
    try:
        tool_input = json.load(sys.stdin).get("tool_input") or {}
    except Exception:
        return 0
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return 0

    root = repo_root()
    try:
        rel = Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0  # outside the repo (scratch files, memory, ...)

    owner, me = owner_of(rel, load_rules(root)), whoami(root)
    if owner is None or owner == me:
        return 0

    if owner == "shared":
        reason = (f"OWNERSHIP: {rel} is a SHARED contract file (see OWNERS). Change it only in a small "
                  f"'[contract]' PR the whole team knows about (docs/WORK_PLAN.md §6).")
    else:
        reason = (f"OWNERSHIP: {rel} is owned by {owner}; you are {me or 'unknown (set VSEARCH_OWNER)'}. "
                  f"Editing it risks merge conflicts. Prefer adding a request for {owner} under "
                  f"'Requests to others' in your docs/team/STATUS-<you>.md (docs/WORK_PLAN.md §6).")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

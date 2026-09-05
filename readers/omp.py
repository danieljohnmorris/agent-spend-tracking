#!/usr/bin/env python3
"""Cost reader for omp session files.

Session layout under ~/.omp/agent/sessions/<encoded-cwd>/:
    <ts>_<session-id>.jsonl              parent session transcript
    <ts>_<session-id>/<Name>.jsonl       per-subagent transcripts
    <ts>_<session-id>/__advisor.jsonl    advisor side-sessions
    <ts>_<session-id>/*.log, local/      tool logs and attachments (ignored)

Verified schema (2026-09-05, against 397 local session files):
  - usage is PER-API-CALL, not cumulative
  - one record per API response; responseId is unique (no dedupe needed,
    enforced anyway as belt-and-braces)
  - error responses carry usage zeros -> skipped via errorMessage/errorId
  - message.usage.cost.total is omp-computed USD, priced per provider
  - cttl (cache TTL split, e.g. {"ephemeral5m": N}) present on Anthropic
    messages only
  - records carry NO branch/git metadata; only the session-header cwd.
    Branch attribution must come from git history (M2), not this reader.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".omp/agent/sessions"


@dataclass
class FileSpend:
    path: Path
    cost: float = 0.0
    calls: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    by_model: dict = field(default_factory=lambda: defaultdict(float))

    def add(self, msg: dict) -> None:
        usage = msg["usage"]
        total = usage.get("cost", {}).get("total", 0.0) or 0.0
        self.cost += total
        self.calls += 1
        self.output_tokens += usage.get("output", 0) or 0
        self.cache_write_tokens += usage.get("cacheWrite", 0) or 0
        self.by_model[msg.get("model", "?")] += total


def _assistant_ok(msg: dict) -> bool:
    return (
        msg.get("role") == "assistant"
        and isinstance(msg.get("usage"), dict)
        and not msg.get("errorMessage")
        and not msg.get("errorId")
    )


def read_file(path: Path) -> FileSpend:
    spend = FileSpend(path)
    seen: set[str] = set()
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message")
            if not isinstance(msg, dict) or not _assistant_ok(msg):
                continue
            rid = msg.get("responseId")
            if rid is not None:
                if rid in seen:
                    continue  # duplicate API response; never double-count
                seen.add(rid)
            spend.add(msg)
    return spend


@dataclass
class Session:
    parent: FileSpend
    children: list[FileSpend] = field(default_factory=list)

    @property
    def cost(self) -> float:
        return self.parent.cost + sum(c.cost for c in self.children)

    @property
    def cwd(self) -> str | None:
        with self.parent.path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") == "session":
                    return rec.get("cwd")
        return None


def session_start(path: Path) -> datetime | None:
    with path.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "session" and rec.get("timestamp"):
                return datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc)


def iter_sessions(root: Path):
    for parent_file in sorted(root.glob("*/*.jsonl")):
        sdir = parent_file.with_suffix("")
        children = sorted(p for p in sdir.glob("*.jsonl")) if sdir.is_dir() else []
        yield Session(parent=read_file(parent_file), children=[read_file(c) for c in children])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--days", type=int, default=30, help="only sessions started within N days")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    rows = [s for s in iter_sessions(args.root) if (session_start(s.parent.path) or cutoff) >= cutoff]

    if args.json:
        print(json.dumps(
            [{"cwd": s.cwd, "parent": str(s.parent.path), "cost": round(s.cost, 4),
              "children": [{"name": c.path.name, "cost": round(c.cost, 4), "calls": c.calls} for c in s.children]}
             for s in rows], indent=2))
        return 0

    total = 0.0
    models: dict[str, float] = defaultdict(float)
    rows.sort(key=lambda s: s.cost, reverse=True)
    for s in rows:
        total += s.cost
        for fs in [s.parent, *s.children]:
            for m, c in fs.by_model.items():
                models[m] += c
        if s.cost == 0:
            continue
        cwd = s.cwd or "?"
        print(f"${s.cost:9.2f}  {cwd}")
        subs_cost = sum(c.cost for c in s.children)
        if subs_cost > 0:
            top = max(s.children, key=lambda c: c.cost)
            print(f"    ${subs_cost:8.2f}  {len(s.children)} subagents (top: {top.path.name} ${top.cost:.2f})")
    print("-" * 50)
    for m, c in sorted(models.items(), key=lambda kv: -kv[1]):
        print(f"${c:9.2f}  {m}")
    print(f"${total:9.2f}  TOTAL ({len(rows)} sessions, last {args.days}d)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

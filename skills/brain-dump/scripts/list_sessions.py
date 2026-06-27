#!/usr/bin/env python3
"""Index Cursor, Claude Code, Codex, and Copilot CLI agent sessions within a
time window.

Scans the chat stores and reports the sessions whose activity overlaps a
window:

  Cursor       ~/.cursor/projects/*/agent-transcripts/<uuid>/<uuid>.jsonl
               (local IDE chats AND cloud / background / worktree sessions,
               which live in separate project folders)
  Claude Code  ~/.claude/projects/<flattened-path>/<uuid>.jsonl
  Codex        ~/.codex/sessions/YYYY/MM/DD/rollout-*-<uuid>.jsonl
  Copilot CLI  ~/.copilot/session-state/<uuid>/events.jsonl

Window resolution (highest precedence first):
  --since / --until    explicit ISO timestamps
  positional WINDOW    a duration (30m, 8h, 2d, 1w), a date (YYYY-MM-DD),
                       or the keywords `today` / `yesterday`
  (nothing)            since the last invocation (~/.brain-dump/last_run), until now;
                       on the first ever run, falls back to the last 24h

Use --mark-run to record "now" as the last invocation time and exit; the
brain-dump skill calls this as its final step, after the note is composed.
The last-run state is shared across all stores (Cursor, Claude Code, Codex,
Copilot CLI).
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TS_RE = re.compile(r"<timestamp>(.*?)</timestamp>")
UQ_RE = re.compile(r"<user_query>(.*?)</user_query>", re.S)
OFFSET_RE = re.compile(r"\(UTC([+-])(\d+):(\d+)\)")
DURATION_RE = re.compile(r"^(\d+)\s*([mhdw])$")
# Harness-injected blocks inside user messages that are not the user's prompt.
INJECTED_BLOCK_RE = re.compile(
    r"<(system-reminder|task-notification|local-command-stdout|ide_opened_file|ide_selection)>"
    r"[\s\S]*?</\1>")
COMMAND_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>")
COMMAND_ARGS_RE = re.compile(r"<command-args>([\s\S]*?)</command-args>")
UUID_FILE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# Shared across every installed copy of this skill (Cursor, Claude Code, Codex,
# Copilot), so marking a run from any tool advances one window for all of them.
DEFAULT_STATE = Path.home() / ".brain-dump" / "last_run"
DEFAULT_CURSOR_ROOT = Path.home() / ".cursor" / "projects"
DEFAULT_CLAUDE_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_CODEX_ROOT = Path.home() / ".codex" / "sessions"
DEFAULT_COPILOT_ROOT = Path.home() / ".copilot" / "session-state"
CLAUDE_SESSIONS_DIR = Path.home() / ".claude" / "sessions"


def local_tz() -> dt.tzinfo:
    tz = dt.datetime.now().astimezone().tzinfo
    return tz if tz is not None else dt.timezone.utc


def parse_embedded_ts(text: str):
    """Parse a Cursor transcript <timestamp> string into an aware UTC datetime."""
    text = text.strip()
    off = OFFSET_RE.search(text)
    tz = dt.timezone.utc
    if off:
        sign, hh, mm = off.group(1), int(off.group(2)), int(off.group(3))
        delta = dt.timedelta(hours=hh, minutes=mm)
        tz = dt.timezone(-delta if sign == "-" else delta)
        text = OFFSET_RE.sub("", text).strip()
    try:
        naive = dt.datetime.strptime(text, "%A, %b %d, %Y, %I:%M %p")
    except ValueError:
        return None
    return naive.replace(tzinfo=tz).astimezone(dt.timezone.utc)


def parse_claude_ts(text: str):
    """Parse a Claude Code ISO8601 timestamp into an aware UTC datetime."""
    try:
        d = dt.datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def resolve_window(args):
    """Return (since_utc, until_utc) as aware UTC datetimes."""
    tz = local_tz()
    now = dt.datetime.now(dt.timezone.utc)

    if args.since or args.until:
        since = _parse_iso(args.since, tz) if args.since else None
        until = _parse_iso(args.until, tz) if args.until else now
        if since is None:
            since = until - dt.timedelta(days=1)
        return since, until

    win = (args.window or "").strip().lower()
    if win:
        m = DURATION_RE.match(win)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            mult = {"m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
            return now - dt.timedelta(seconds=n * mult), now
        if win in ("today", "yesterday"):
            today = dt.datetime.now(tz).date()
            day = today if win == "today" else today - dt.timedelta(days=1)
            start = dt.datetime.combine(day, dt.time.min, tz)
            return start.astimezone(dt.timezone.utc), (start + dt.timedelta(days=1)).astimezone(dt.timezone.utc)
        try:
            day = dt.date.fromisoformat(win)
        except ValueError:
            sys.exit(f"error: cannot parse window '{args.window}' (use a duration like 2d, a date YYYY-MM-DD, or today/yesterday)")
        start = dt.datetime.combine(day, dt.time.min, tz)
        return start.astimezone(dt.timezone.utc), (start + dt.timedelta(days=1)).astimezone(dt.timezone.utc)

    # default: since last run
    last = read_last_run(args.state_file)
    since = last if last is not None else now - dt.timedelta(days=1)
    return since, now


def _parse_iso(s: str, tz: dt.tzinfo):
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=tz)
    return d.astimezone(dt.timezone.utc)


def read_last_run(state_file: Path):
    try:
        raw = Path(state_file).read_text().strip()
    except FileNotFoundError:
        return None
    if not raw:
        return None
    try:
        return _parse_iso(raw, local_tz())
    except ValueError:
        return None


def scan_cursor_session(path: Path):
    """Read one Cursor transcript; return its activity span, turn count, first query."""
    timestamps = []
    user_turns = 0
    first_query = None
    try:
        with path.open() as f:
            for line in f:
                if '"turn_ended"' in line:
                    continue
                if "<timestamp>" not in line and '"role":"user"' not in line and '"role": "user"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("role") != "user":
                    continue
                content = (obj.get("message") or {}).get("content") or []
                text = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
                user_turns += 1
                for ts in TS_RE.findall(text):
                    parsed = parse_embedded_ts(ts)
                    if parsed:
                        timestamps.append(parsed)
                if first_query is None:
                    q = UQ_RE.findall(text)
                    if q:
                        first_query = re.sub(r"\s+", " ", q[0]).strip()
    except OSError:
        return None

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    start = min(timestamps) if timestamps else mtime
    end = max(max(timestamps), mtime) if timestamps else mtime
    sub_dir = path.parent / "subagents"
    subagents = len(list(sub_dir.glob("*.jsonl"))) if sub_dir.is_dir() else 0
    return {
        "path": str(path),
        "uuid": path.stem,
        "project": path.parents[2].name,
        "source": "cursor",
        "title": "",
        "start": start,
        "end": end,
        "turns": user_turns,
        "size": path.stat().st_size,
        "subagents": subagents,
        "first_query": first_query or "",
    }


def clean_claude_user_text(content) -> str:
    """Extract the human-typed prompt from a Claude Code user line's content.
    Returns "" when the line carries no real prompt (tool results, stdout
    echoes, injected system reminders)."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    else:
        return ""
    m = COMMAND_NAME_RE.search(text)
    if m:
        args = COMMAND_ARGS_RE.search(text)
        arg_text = args.group(1).strip() if args else ""
        return (m.group(1).strip() + (" " + arg_text if arg_text else "")).strip()
    return INJECTED_BLOCK_RE.sub("", text).strip()


CODEX_REQUEST_MARKER = "## My request for Codex:"


def clean_codex_user_text(message) -> str:
    """Extract the human request from a Codex `event_msg/user_message`, dropping
    the IDE-context preamble ("# Context from my IDE setup: ... ## My request for
    Codex: <real>") when present."""
    if not isinstance(message, str):
        return ""
    text = message
    if CODEX_REQUEST_MARKER in text:
        text = text.split(CODEX_REQUEST_MARKER, 1)[1]
    return text.strip()


def scan_claude_session(path: Path):
    """Read one Claude Code transcript; return its activity span, turn count,
    first query, and AI-generated title."""
    timestamps = []
    user_turns = 0
    first_query = None
    title = ""
    cwd = None
    try:
        with path.open() as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                typ = obj.get("type")
                if typ == "ai-title":
                    title = obj.get("aiTitle") or title
                    continue
                ts = obj.get("timestamp")
                if isinstance(ts, str):
                    parsed = parse_claude_ts(ts)
                    if parsed:
                        timestamps.append(parsed)
                if cwd is None and isinstance(obj.get("cwd"), str):
                    cwd = obj["cwd"]
                if typ != "user" or obj.get("isMeta"):
                    continue
                text = clean_claude_user_text((obj.get("message") or {}).get("content"))
                if not text:
                    continue
                user_turns += 1
                if first_query is None:
                    first_query = re.sub(r"\s+", " ", text).strip()
    except OSError:
        return None

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    start = min(timestamps) if timestamps else mtime
    end = max(max(timestamps), mtime) if timestamps else mtime
    sub_dir = path.parent / path.stem / "subagents"
    subagents = len(list(sub_dir.glob("agent-*.jsonl"))) if sub_dir.is_dir() else 0
    return {
        "path": str(path),
        "uuid": path.stem,
        "project": Path(cwd).name if cwd else path.parent.name,
        "source": "claude",
        "title": title,
        "start": start,
        "end": end,
        "turns": user_turns,
        "size": path.stat().st_size,
        "subagents": subagents,
        "first_query": first_query or "",
    }


def scan_codex_session(path: Path):
    """Read one Codex rollout transcript; return its activity span, real
    user-turn count, first query, and thread title."""
    timestamps = []
    user_turns = 0
    first_query = None
    title = ""
    cwd = None
    sid = None
    subagents = 0
    try:
        with path.open() as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                ts = obj.get("timestamp")
                if isinstance(ts, str):
                    parsed = parse_claude_ts(ts)
                    if parsed:
                        timestamps.append(parsed)
                rt = obj.get("type")
                payload = obj.get("payload") or {}
                if rt == "session_meta":
                    if cwd is None and isinstance(payload.get("cwd"), str):
                        cwd = payload["cwd"]
                    sid = sid or payload.get("id")
                elif rt == "event_msg":
                    pt = payload.get("type")
                    if pt == "thread_name_updated":
                        title = payload.get("thread_name") or title
                    elif pt == "user_message":
                        text = clean_codex_user_text(payload.get("message"))
                        if text:
                            user_turns += 1
                            if first_query is None:
                                first_query = re.sub(r"\s+", " ", text).strip()
                elif rt == "response_item" and payload.get("type") == "function_call" \
                        and payload.get("name") == "spawn_agent":
                    subagents += 1
    except OSError:
        return None

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    start = min(timestamps) if timestamps else mtime
    end = max(max(timestamps), mtime) if timestamps else mtime
    m = UUID_RE.search(path.stem)
    return {
        "path": str(path),
        "uuid": sid or (m.group(0) if m else path.stem),
        "project": Path(cwd).name if cwd else "codex",
        "source": "codex",
        "title": title,
        "start": start,
        "end": end,
        "turns": user_turns,
        "size": path.stat().st_size,
        "subagents": subagents,
        "first_query": first_query or "",
    }


def scan_copilot_session(path: Path):
    """Read one Copilot CLI events.jsonl; return its activity span, user-turn
    count, and first query. The session id is the parent directory name."""
    timestamps = []
    user_turns = 0
    first_query = None
    cwd = None
    try:
        with path.open() as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                ts = obj.get("timestamp")
                if isinstance(ts, str):
                    parsed = parse_claude_ts(ts)
                    if parsed:
                        timestamps.append(parsed)
                t = obj.get("type")
                data = obj.get("data") or {}
                if t == "session.start":
                    ctx = data.get("context") or {}
                    if cwd is None and isinstance(ctx.get("cwd"), str):
                        cwd = ctx["cwd"]
                    st = data.get("startTime")
                    if isinstance(st, str):
                        parsed = parse_claude_ts(st)
                        if parsed:
                            timestamps.append(parsed)
                elif t == "user.message":
                    content = data.get("content")
                    if isinstance(content, str) and content.strip():
                        user_turns += 1
                        if first_query is None:
                            first_query = re.sub(r"\s+", " ", content).strip()
    except OSError:
        return None

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    start = min(timestamps) if timestamps else mtime
    end = max(max(timestamps), mtime) if timestamps else mtime
    return {
        "path": str(path),
        "uuid": path.parent.name,
        "project": Path(cwd).name if cwd else path.parent.name,
        "source": "copilot",
        "title": "",
        "start": start,
        "end": end,
        "turns": user_turns,
        "size": path.stat().st_size,
        "subagents": 0,
        "first_query": first_query or "",
    }


def find_sessions(cursor_root, claude_root, codex_root, copilot_root,
                  since, until, exclude, sources, include_empty=False):
    results = []
    if "cursor" in sources and cursor_root.is_dir():
        for project in sorted(cursor_root.iterdir()):
            tdir = project / "agent-transcripts"
            if not tdir.is_dir():
                continue
            for jsonl in tdir.glob("*/*.jsonl"):
                if jsonl.stem in exclude:
                    continue
                info = scan_cursor_session(jsonl)
                if info is not None:
                    results.append(info)
    if "claude" in sources and claude_root.is_dir():
        for project in sorted(claude_root.iterdir()):
            if not project.is_dir():
                continue
            for jsonl in project.glob("*.jsonl"):
                if not UUID_FILE_RE.match(jsonl.stem) or jsonl.stem in exclude:
                    continue
                info = scan_claude_session(jsonl)
                if info is not None:
                    results.append(info)
    if "codex" in sources and codex_root.is_dir():
        for jsonl in sorted(codex_root.rglob("rollout-*.jsonl")):
            info = scan_codex_session(jsonl)
            if info is not None and info["uuid"] not in exclude:
                results.append(info)
    if "copilot" in sources and copilot_root.is_dir():
        for events in sorted(copilot_root.glob("*/events.jsonl")):
            if events.parent.name in exclude:
                continue
            info = scan_copilot_session(events)
            if info is not None:
                results.append(info)
    results = [
        s for s in results
        if s["end"] >= since and s["start"] <= until and (include_empty or s["turns"] > 0)
    ]
    results.sort(key=lambda s: s["end"])
    return results


def parent_pid(pid):
    """Return the parent pid of `pid`, cross-platform. Tries Linux /proc first,
    then falls back to `ps` (macOS / BSD, which have no /proc). Returns None when
    it can't be determined."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        # ppid is the 2nd field after the parenthesised comm, which may itself
        # contain spaces or ')'
        return int(stat.rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        pass
    try:
        out = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True, text=True)
        return int(out.stdout.strip())
    except (OSError, ValueError):
        return None


def detect_current_claude_session():
    """Return the sessionId of the live Claude Code session this process runs
    under, by matching pids from ~/.claude/sessions/*.json against the parent
    process chain. Returns None when not running under Claude Code."""
    pid_map = {}
    if CLAUDE_SESSIONS_DIR.is_dir():
        for f in CLAUDE_SESSIONS_DIR.glob("*.json"):
            try:
                obj = json.loads(f.read_text())
                pid_map[int(obj["pid"])] = str(obj["sessionId"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
    pid = os.getpid()
    seen = set()
    while pid and pid > 1 and pid not in seen:
        seen.add(pid)
        if pid in pid_map:
            return pid_map[pid]
        pid = parent_pid(pid)
    return None


def human_size(n):
    size = float(n)
    for unit in ("B", "K", "M", "G"):
        if size < 1024 or unit == "G":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024


def fmt_local(d):
    return d.astimezone(local_tz()).strftime("%Y-%m-%d %H:%M")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("window", nargs="?", help="duration (2d, 8h), date (YYYY-MM-DD), or today/yesterday")
    ap.add_argument("--since", help="explicit ISO start")
    ap.add_argument("--until", help="explicit ISO end")
    ap.add_argument("--source", choices=["cursor", "claude", "codex", "copilot", "all"], default="all", help="which chat store(s) to scan")
    ap.add_argument("--cursor-root", default=str(DEFAULT_CURSOR_ROOT), help="Cursor projects root dir")
    ap.add_argument("--claude-root", default=str(DEFAULT_CLAUDE_ROOT), help="Claude Code projects root dir")
    ap.add_argument("--codex-root", default=str(DEFAULT_CODEX_ROOT), help="Codex sessions root dir")
    ap.add_argument("--copilot-root", default=str(DEFAULT_COPILOT_ROOT), help="Copilot CLI session-state root dir")
    ap.add_argument("--state-file", default=str(DEFAULT_STATE), help="last-run state file")
    ap.add_argument("--exclude-session", action="append", default=[], help="session uuid(s) to skip")
    ap.add_argument("--exclude-current", action="store_true", help="auto-exclude the live Claude Code session this script runs under")
    ap.add_argument("--include-empty", action="store_true", help="keep sessions with zero real user turns")
    ap.add_argument("--mark-run", action="store_true", help="write now to state file and exit")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.mark_run:
        state = Path(args.state_file)
        state.parent.mkdir(parents=True, exist_ok=True)
        now_iso = dt.datetime.now(local_tz()).isoformat(timespec="seconds")
        state.write_text(now_iso + "\n")
        print(f"marked last_run = {now_iso}")
        return

    exclude = set(args.exclude_session)
    if args.exclude_current:
        current = detect_current_claude_session()
        if current:
            exclude.add(current)
            print(f"--exclude-current: excluding live Claude Code session {current}", file=sys.stderr)
        else:
            print("--exclude-current: no live Claude Code session found in process ancestry", file=sys.stderr)

    since, until = resolve_window(args)
    sources = {"cursor", "claude", "codex", "copilot"} if args.source == "all" else {args.source}
    sessions = find_sessions(
        Path(args.cursor_root).expanduser(), Path(args.claude_root).expanduser(),
        Path(args.codex_root).expanduser(), Path(args.copilot_root).expanduser(),
        since, until, exclude, sources, args.include_empty)

    if args.json:
        out = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "count": len(sessions),
            "sessions": [
                {**s, "start": s["start"].isoformat(), "end": s["end"].isoformat()} for s in sessions
            ],
        }
        print(json.dumps(out, indent=2))
        return

    print(f"window: {fmt_local(since)}  ->  {fmt_local(until)}  (local)")
    print(f"sessions: {len(sessions)}\n")
    cur_group = None
    for s in sessions:
        group = (s["source"], s["project"])
        if group != cur_group:
            cur_group = group
            print(f"## {s['source']}: {s['project']}")
        line = (
            f"  [{fmt_local(s['start'])} -> {fmt_local(s['end'])}] "
            f"turns={s['turns']} {human_size(s['size'])}"
        )
        if s["subagents"]:
            line += f" subagents={s['subagents']}"
        print(line)
        print(f"    {s['path']}")
        if s["title"]:
            print(f"    t: {s['title']}")
        if s["first_query"]:
            print(f"    q: {s['first_query'][:160]}")
    if not sessions:
        print("(no sessions in window)")


if __name__ == "__main__":
    main()

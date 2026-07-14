#!/usr/bin/env python3
"""agent-memory — cross-agent durable session memory for coding agents.

One shared store (~/.agent-memory) gives Claude Code, Codex, Cursor, and
Copilot CLI a common working-state checkpoint per session, a mechanical
event journal, cross-session/cross-agent resume, staleness detection, and
history search. Each agent's hooks call this script with its native JSON
payload on stdin:

    agent_memory.py hook <agent> <event>

where <agent> is claude|codex|cursor|copilot and <event> is one of the
normalized lifecycle events: session-start, prompt, post-tool, stop,
pre-compact, post-compact, session-end.

Hook invocations NEVER fail the host agent: any internal error is logged to
~/.agent-memory/log/hooks.log and the process exits 0 with no output.

Other subcommands (run by the model or the user):
    adopt <source-session> --into <current-session>   continue earlier work
    fresh --session <current-session>                  archive state, start blank
    status [--all-projects]                            list sessions and states
    search <regex> [--all-projects] [--limit N]        query persisted memory
    show <session>                                     dump one session's state+journal
    doctor [--json]                                    validate installation
    version

Store layout (schema 1):
    ~/.agent-memory/
      store.json
      log/hooks.log
      sessions-index/<agent>-<session-id>       -> project dir name (fast path)
      projects/<name>-<hash10>/
        project.json
        sessions/<agent>-<session-id>/
          meta.json      (single writer: this session's hooks)
          state.md       (written by the MODEL; the authoritative checkpoint)
          journal.jsonl  (appended by hooks; mechanical event record)
          archive/       (superseded state files from `fresh`)
        archive/<agent>-<session-id>/           (pruned sessions)

Python: stdlib only; compatible with 3.8+ (macOS + Ubuntu hosts).
"""

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

try:
    import fcntl
except ImportError:  # non-POSIX; locking degrades to best-effort no-op
    fcntl = None

SCHEMA = 1
AGENTS = ("claude", "codex", "cursor", "copilot")
EVENTS = ("session-start", "prompt", "post-tool", "stop",
          "pre-compact", "post-compact", "session-end")

# --- tunables (env-overridable) ---------------------------------------------


def _env_int(name, default):
    try:
        return int(os.environ.get(name, ""))
    except ValueError:
        return default


def store_root():
    return os.environ.get("AGENT_MEMORY_HOME") or os.path.join(
        os.path.expanduser("~"), ".agent-memory")


ACTIVE_MIN = _env_int("AGENT_MEMORY_ACTIVE_MIN", 15)     # heartbeat freshness
GAP_MIN = _env_int("AGENT_MEMORY_GAP_MIN", 45)           # resume-gap detector
STALE_TOOLS = _env_int("AGENT_MEMORY_STALE_TOOLS", 3)    # actions before stale
NUDGE_TOOLS = _env_int("AGENT_MEMORY_NUDGE_TOOLS", 5)    # actions before mid-turn
                                                         # nudge; 0 disables
NUDGE_COOLDOWN_MIN = _env_int("AGENT_MEMORY_NUDGE_COOLDOWN_MIN", 5)
MAX_INJECT = _env_int("AGENT_MEMORY_MAX_INJECT", 8000)   # bytes; Copilot caps 10KB
# Codex spills hook output past ~2,500 tokens into a file the model may not
# read; keep its injections well under that (~6KB of dense text).
INJECT_BUDGETS = {"codex": 6000}
MAX_STATE_LINES = 120                                    # guidance, warned above
CANDIDATES = 3                                           # offered at session start
JOURNAL_ROTATE = 2 * 1024 * 1024                         # bytes
LOG_ROTATE = 512 * 1024


def inject_budget(agent):
    return min(MAX_INJECT, INJECT_BUDGETS.get(agent, MAX_INJECT))

STATE_TEMPLATE = """# Working state
Status: in-progress

## Objective

## Constraints & decisions

## Done (verified)

## Failed hypotheses (still relevant)

## Now (exact stopping point)

## Next

## Open questions
"""

# Tool names that indicate real work (staleness signal), lowercased substrings.
MUTATING_TOOLS = re.compile(
    r"(?i)\b(bash|shell|edit|write|create|apply_patch|multiedit|"
    r"notebookedit|str_replace|task)\b")


# --- small utilities ---------------------------------------------------------


def now_ts():
    return time.time()


def iso(ts=None):
    dt = datetime.fromtimestamp(ts if ts is not None else time.time(),
                                tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"


def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def _mkdirs(path):
    os.makedirs(path, exist_ok=True)


def atomic_write(path, data):
    """Write text atomically (tmp file + rename)."""
    _mkdirs(os.path.dirname(path))
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_json(path, obj):
    atomic_write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def read_text(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return default


@contextmanager
def locked(path, timeout=3.0):
    """Best-effort advisory lock. Yields True when held, False on timeout or
    unsupported platform — callers proceed either way (never stall the agent),
    the lock only shrinks race windows between concurrent hook processes."""
    if fcntl is None:
        yield False
        return
    _mkdirs(os.path.dirname(path))
    f = open(path, "a")
    got = False
    try:
        import errno
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError as e:
                # only real contention is worth retrying; ENOLCK/ENOTSUP etc.
                # (network/FUSE homes) would otherwise stall every hook for
                # the full timeout
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN,
                                   errno.EACCES):
                    break
                time.sleep(0.05)
        yield got
    finally:
        if got:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        f.close()


def append_line(path, line):
    """Single-write append; safe for concurrent same-session hook processes."""
    _mkdirs(os.path.dirname(path))
    try:
        if os.path.getsize(path) > JOURNAL_ROTATE:
            os.replace(path, path + ".1")
    except OSError:
        pass
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def log_error(msg):
    try:
        path = os.path.join(store_root(), "log", "hooks.log")
        _mkdirs(os.path.dirname(path))
        try:
            if os.path.getsize(path) > LOG_ROTATE:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (iso(), msg))
    except OSError:
        pass


def truncate(text, limit, marker="\n...[truncated — read the file itself]"):
    """Cap text at `limit` BYTES. The marker's em-dash made the old
    char-count arithmetic overshoot by 2 bytes — enough to breach a
    platform's hard cap exactly at the boundary."""
    if len(text.encode("utf-8", "replace")) <= limit:
        return text
    room = max(0, limit - len(marker.encode("utf-8")))
    enc = text.encode("utf-8", "replace")[:room]
    # "ignore" drops a trailing partial character instead of inflating it
    # into a 3-byte U+FFFD, keeping the result under the byte budget.
    return enc.decode("utf-8", "ignore") + marker


def sanitize_name(name):
    out = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-.") or "project"
    return out[:40]


def sha10(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


# --- project identity --------------------------------------------------------


def _git(args, cwd):
    try:
        p = subprocess.run(["git", "-C", cwd] + args, capture_output=True,
                           text=True, timeout=10)
        if p.returncode == 0:
            return p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def normalize_remote(url):
    """git@github.com:me/repo.git / https://github.com/me/repo -> github.com/me/repo"""
    u = url.strip()
    u = re.sub(r"^[a-z+]+://", "", u)          # scheme
    u = re.sub(r"^[^@/]+@", "", u)             # user@
    u = u.replace(":", "/", 1) if ("@" not in u and ":" in u.split("/")[0]) else u
    u = re.sub(r"\.git/?$", "", u)
    return u.rstrip("/").lower()


def project_identity(cwd):
    """Resolve a stable, collision-resistant project identity for cwd.

    Precedence:
      1. git root commit  — identical across clones and worktrees of a repo
      2. normalized remote URL — for shallow clones (their root commit lies)
      3. realpath of the toplevel/cwd — non-git directories

    Returns dict: kind, key, name, hash, toplevel, worktree, remote.
    """
    real = os.path.realpath(cwd)
    top = _git(["rev-parse", "--show-toplevel"], real)
    worktree = os.path.realpath(top) if top else real
    remote = _git(["config", "--get", "remote.origin.url"], real) if top else None
    kind, key = None, None
    if top:
        shallow = _git(["rev-parse", "--is-shallow-repository"], real)
        if shallow != "true":
            roots = _git(["rev-list", "--max-parents=0", "HEAD"], real)
            if roots:
                kind, key = "git-root-commit", sorted(roots.split())[0]
        if key is None and remote:
            kind, key = "git-remote", normalize_remote(remote)
        if key is None:
            kind, key = "path", worktree
    else:
        kind, key = "path", real
    # Prefer a name derived from the remote: deterministic across worktrees
    # and clones (worktree basenames differ per checkout, which would make
    # concurrent first-time starts mint differently-named dirs).
    if remote:
        base = normalize_remote(remote).rsplit("/", 1)[-1]
    else:
        base = os.path.basename(worktree)
    return {
        "kind": kind,
        "key": key,
        "name": sanitize_name(base),
        "hash": sha10(kind + ":" + key),
        "toplevel": top,
        "worktree": worktree,
        "remote": remote,
    }


def projects_dir():
    return os.path.join(store_root(), "projects")


def find_project_dir(ident):
    """Locate an existing project dir by hash suffix, else derive a new path.

    Lookup is by hash only: the human-readable prefix may differ between the
    clone that created the dir and the current checkout's basename.
    """
    pdir = projects_dir()
    suffix = "-" + ident["hash"]
    try:
        for entry in sorted(os.listdir(pdir)):
            if entry.endswith(suffix):
                return os.path.join(pdir, entry)
    except OSError:
        pass
    return os.path.join(pdir, ident["name"] + suffix)


def ensure_project(cwd):
    """Resolve (and record) the project for cwd. Returns (proj_dir, ident)."""
    ident = project_identity(cwd)
    proj = find_project_dir(ident)
    if not os.path.isdir(proj):
        # First session for this identity: create under the store lock and
        # re-check, so two concurrent first-starts (e.g. from two worktrees)
        # cannot mint two dirs for one identity hash.
        with locked(os.path.join(store_root(), ".projects.lock")):
            proj = find_project_dir(ident)
            _mkdirs(os.path.join(proj, "sessions"))
    _mkdirs(os.path.join(proj, "sessions"))
    pj_path = os.path.join(proj, "project.json")
    pj = read_json(pj_path) or {
        "schema": SCHEMA,
        "identity": {"kind": ident["kind"], "key": ident["key"]},
        "created_at": iso(),
        "worktrees": {},
    }
    wt = pj.setdefault("worktrees", {})
    entry = wt.setdefault(ident["worktree"], {})
    entry["last_seen"] = iso()
    if ident["remote"]:
        pj["remote"] = ident["remote"]
    write_json(pj_path, pj)
    return proj, ident


# --- session records ---------------------------------------------------------


def session_key(agent, session_id):
    sid = re.sub(r"[^A-Za-z0-9-]", "", str(session_id))[:64] or "unknown"
    return "%s-%s" % (agent, sid)


def session_dir(proj, key):
    return os.path.join(proj, "sessions", key)


def index_path(key):
    return os.path.join(store_root(), "sessions-index", key)


def lookup_project_for(key):
    """Fast path: map a session key to its project dir without running git."""
    name = read_text(index_path(key)).strip()
    if name:
        proj = os.path.join(projects_dir(), name)
        if os.path.isdir(proj):
            return proj
    return None


def state_path(sdir):
    return os.path.join(sdir, "state.md")


def meta_path(sdir):
    return os.path.join(sdir, "meta.json")


def journal_path(sdir):
    return os.path.join(sdir, "journal.jsonl")


def journal(sdir, ev, **fields):
    rec = {"ts": iso(), "ev": ev}
    rec.update({k: v for k, v in fields.items() if v is not None})
    append_line(journal_path(sdir), json.dumps(rec, ensure_ascii=False))


def load_meta(sdir):
    return read_json(meta_path(sdir), {})


def save_meta(sdir, meta):
    write_json(meta_path(sdir), meta)


def ensure_session(proj, ident, agent, session_id, norm):
    """Create or refresh the session record; returns (sdir, meta, created)."""
    key = session_key(agent, session_id)
    sdir = session_dir(proj, key)
    created = not os.path.isdir(sdir)
    _mkdirs(sdir)
    meta = load_meta(sdir)
    if not meta:
        meta = {
            "schema": SCHEMA,
            "key": key,
            "agent": agent,
            "session_id": str(session_id),
            "created_at": iso(),
            "worktree": ident["worktree"],
            "counts": {"prompts": 0, "tools": 0},
            "status": "active",
        }
        created = True
    meta["last_event_ts"] = iso()
    meta["status"] = "active" if norm.get("event") != "session-end" else meta.get("status", "active")
    if norm.get("cwd"):
        meta["cwd_last"] = norm["cwd"]
    if norm.get("transcript_path"):
        meta["transcript_path"] = norm["transcript_path"]
    if created:
        sp = state_path(sdir)
        if not os.path.exists(sp):
            atomic_write(sp, STATE_TEMPLATE)
            meta["state_template_sha"] = sha10(STATE_TEMPLATE)
    atomic_write(index_path(key), os.path.basename(proj) + "\n")
    return sdir, meta, created


# --- payload adapters (per-agent stdin normalization) ------------------------
#
# Field names below are the verified on-wire contracts (2026-07):
#   claude : session_id, cwd, source, prompt, tool_name/tool_input,
#            transcript_path, stop_hook_active, trigger, reason
#   codex  : same shape as claude (hookSpecificOutput family), no SessionEnd
#   cursor : session_id/conversation_id, workspace_roots (NO cwd), snake_case
#   copilot: sessionId, cwd, toolName, toolArgs (may be a JSON *string*),
#            timestamps are epoch ms, sessionEnd reason / agentStop stopReason


def _primary_arg(tool_input):
    # Nearly untruncated here so touches_store sees the full argument (a
    # heredoc checkpoint command may mention the state path deep inside);
    # the journal write truncates for storage.
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except ValueError:
            return tool_input[:2000]
    if not isinstance(tool_input, dict):
        return None
    for k in ("file_path", "path", "filePath", "command", "cmd", "pattern",
              "query", "url", "description"):
        v = tool_input.get(k)
        if isinstance(v, str) and v:
            return v[:2000]
    return None


def adapt_claude(event, p):
    return {
        "session_id": p.get("session_id"),
        "cwd": p.get("cwd"),
        "source": p.get("source"),
        "prompt": p.get("prompt"),
        "tool_name": p.get("tool_name"),
        "tool_target": _primary_arg(p.get("tool_input")),
        "transcript_path": p.get("transcript_path"),
        "stop_hook_active": bool(p.get("stop_hook_active")),
        "trigger": p.get("trigger"),
        "reason": p.get("reason"),
        # Task-subagent tool calls fire hooks under the parent session id;
        # only those payloads carry agent_id/agent_type (verified 2026-07).
        "subagent": bool(p.get("agent_id") or p.get("agent_type")),
    }


def adapt_codex(event, p):
    n = adapt_claude(event, p)
    n["reason"] = None  # codex has no SessionEnd/reason
    return n


def adapt_cursor(event, p):
    roots = p.get("workspace_roots") or []
    return {
        "session_id": p.get("session_id") or p.get("conversation_id"),
        "cwd": roots[0] if roots else p.get("cwd"),
        "source": None,  # cursor sessionStart has no source field
        "prompt": p.get("prompt"),
        "tool_name": p.get("tool_name"),
        "tool_target": _primary_arg(p.get("tool_input")),
        "transcript_path": p.get("transcript_path"),
        "stop_hook_active": False,
        "trigger": p.get("trigger"),
        "reason": p.get("reason") or p.get("status"),
        "subagent": False,  # no known subagent signal in cursor payloads
    }


def adapt_copilot(event, p):
    return {
        "session_id": p.get("sessionId") or p.get("session_id"),
        "cwd": p.get("cwd"),
        "source": p.get("source"),
        "prompt": p.get("prompt"),
        "tool_name": p.get("toolName") or p.get("tool_name"),
        "tool_target": _primary_arg(p.get("toolArgs") if "toolArgs" in p
                                    else p.get("tool_input")),
        "transcript_path": p.get("transcriptPath") or p.get("transcript_path"),
        "stop_hook_active": False,
        "trigger": p.get("trigger"),
        "reason": p.get("reason") or p.get("stopReason"),
        # copilot-cli #3894: hooks do fire on subagent turns, but the payload
        # carries no discriminator — accept nudges reaching subagents there.
        "subagent": bool(p.get("agentId") or p.get("agentType")),
    }


ADAPTERS = {"claude": adapt_claude, "codex": adapt_codex,
            "cursor": adapt_cursor, "copilot": adapt_copilot}


# --- output renderers (per-agent stdout contracts) ----------------------------

CLAUDE_EVENT_NAMES = {"session-start": "SessionStart", "prompt": "UserPromptSubmit",
                      "post-tool": "PostToolUse"}


def render_inject(agent, event, text):
    """Context-injection JSON for agents/events that support it, else None."""
    if agent in ("claude", "codex"):
        name = CLAUDE_EVENT_NAMES.get(event)
        if name:
            return {"hookSpecificOutput": {"hookEventName": name,
                                           "additionalContext": text}}
        return None
    if agent == "cursor":
        if event in ("session-start", "post-tool"):
            return {"additional_context": text}
        return None
    if agent == "copilot":
        if event in ("session-start", "post-tool"):
            return {"additionalContext": text}
        return None
    return None


def render_stop_block(agent, reason):
    if agent in ("claude", "codex", "copilot"):
        return {"decision": "block", "reason": reason}
    if agent == "cursor":
        return {"followup_message": reason}
    return None


CAN_INJECT = {
    ("claude", "session-start"), ("claude", "prompt"), ("claude", "post-tool"),
    ("codex", "session-start"), ("codex", "prompt"), ("codex", "post-tool"),
    ("cursor", "session-start"), ("cursor", "post-tool"),
    ("copilot", "session-start"), ("copilot", "post-tool"),
}


# --- state file helpers -------------------------------------------------------


def state_sections(text):
    """Parse '## Heading' sections -> {heading: body}."""
    out = {}
    current, buf = None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current, buf = m.group(1).strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


def state_status(text):
    m = re.search(r"(?im)^status:\s*(\S+)", text)
    return m.group(1).lower() if m else "in-progress"


def first_line(section_body):
    for line in (section_body or "").splitlines():
        line = line.strip().lstrip("-* ").strip()
        if line:
            return line[:160]
    return ""


def state_is_template(sdir, meta):
    txt = read_text(state_path(sdir))
    return sha10(txt) == meta.get("state_template_sha") or txt.strip() == STATE_TEMPLATE.strip()


def state_mtime(sdir):
    try:
        return os.path.getmtime(state_path(sdir))
    except OSError:
        return None


def journal_text(sdir):
    """Current journal plus the one rotated generation, oldest first."""
    return (read_text(journal_path(sdir) + ".1") + read_text(journal_path(sdir)))


def journal_tool_events(sdir):
    """Yield (ts, tool, target) for journaled tool events, oldest first.

    Only 'tool' events: prompts are conversation, not work — a tool-free Q&A
    session must never be declared stale. A double-registered hook (e.g.
    codex honoring both config.toml and hooks.json) fires twice per tool and
    would double every staleness count and state a wrong n in enforcement
    messages, so identical back-to-back (tool, target) records within 0.5s
    collapse to one. Collapsing must never eat REAL work (that would silently
    disarm the stop block), so it is deliberately narrow: duplicate hook
    processes for one event land near-simultaneously, while genuine
    consecutive tool completions are separated by inference time — and
    records without a target never collapse (distinct NotebookEdit/MCP calls
    share (tool, None) and would alias; a double-fired target-less tool
    counting twice is the safer error, and doctor warns about the duplicate
    registration itself).
    """
    last = None
    for line in journal_text(sdir).splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("ev") != "tool":
            continue
        ts = parse_iso(rec.get("ts", ""))
        if ts is None:
            continue
        sig = (rec.get("tool"), rec.get("target"))
        if (last is not None and sig == last[0] and sig[1] is not None
                and ts - last[1] < 0.5):
            continue
        last = (sig, ts)
        yield ts, rec.get("tool") or "?", rec.get("target")


def significant_events_since(sdir, since_ts):
    """Count journaled state-changing tool calls newer than since_ts."""
    return sum(1 for ts, _t, _a in journal_tool_events(sdir)
               if since_ts is None or ts > since_ts)


def journal_tool_tail(sdir, since_ts, limit=10):
    """-> (last `limit` tool events newer than since_ts, total such events)."""
    events = [e for e in journal_tool_events(sdir)
              if since_ts is None or e[0] > since_ts]
    return events[-limit:], len(events)


def checkpoint_is_stale(sdir, meta):
    """Stale = meaningful activity happened after the last state.md write."""
    mt = state_mtime(sdir)
    n = significant_events_since(sdir, mt)
    if state_is_template(sdir, meta):
        return n >= 1, n  # never checkpointed at all
    return n >= STALE_TOOLS, n


def nudge_text(sdir, meta, n, count):
    """Mid-turn staleness reminder. Factual tone on purpose: imperative
    system-command phrasing can trip Claude's prompt-injection defenses."""
    sp = state_path(sdir)
    if count <= 1:
        return (
            "[agent-memory] %d file-modifying tool calls have run since %s"
            " was last updated. Per your working-memory instructions, update"
            " it now — read it if needed, then one Write rewriting the Now /"
            " Next / Done sections in place to match reality — then continue"
            " the current task. No need to mention this in your response."
            % (n, sp))
    # Escalated wording must only promise what the stop hook will deliver:
    # not in soft mode, not inside the 30-min block rate limit, and not while
    # already running a forced continuation (its stop arrives with
    # stop_hook_active set and is never blocked again).
    enforce = os.environ.get("AGENT_MEMORY_ENFORCE", "block") != "soft"
    last_block = parse_iso(meta.get("last_stop_block", ""))
    will_block = (enforce and not meta.get("stop_block_pending")
                  and (last_block is None
                       or now_ts() - last_block >= 30 * 60))
    if will_block:
        consequence = ("the checkpoint gets forced at end of turn anyway, at"
                       " the price of an extra round — doing it now while"
                       " context is fresh is cheaper")
    else:
        consequence = ("if this session is interrupted, none of this work is"
                       " recoverable")
    return (
        "[agent-memory] %s is still stale — %d uncheckpointed tool calls, and"
        " an earlier reminder was not acted on; %s. One small checkpoint"
        " write, then continue the task." % (sp, n, consequence))


def maybe_nudge(sdir, meta, agent, event):
    """Advisory mid-turn stage of staleness enforcement (stop is the blocking
    stage). Fires at most twice per staleness episode, never within the
    cooldown of any other state-carrying delivery. Session-start stamps
    last_inject, so the first cooldown window after every start/compact is a
    deliberate nudge blackout — the state file was just delivered."""
    if NUDGE_TOOLS <= 0:
        return None
    # Hand-edited/corrupt meta must degrade, not raise: an exception here
    # aborts the whole event before save_meta (take_pending_reinject guards
    # the same corruption class).
    last = meta.get("last_nudge")
    last = last if isinstance(last, dict) else {}
    last_inject = meta.get("last_inject")
    last_inject = last_inject if isinstance(last_inject, dict) else {}
    recent = [parse_iso(last.get("ts", "")),
              parse_iso(last_inject.get("ts", "")),
              parse_iso(meta.get("last_stop_block", ""))]
    recent = [t for t in recent if t is not None]
    if recent and now_ts() - max(recent) < NUDGE_COOLDOWN_MIN * 60:
        return None
    last_ts = parse_iso(last.get("ts", ""))
    mt = state_mtime(sdir)
    # A state write after the previous nudge closes the episode; a missing
    # state file counts as ignored (never TypeError on mt=None).
    ignored = last_ts is not None and (mt is None or mt < last_ts)
    if ignored and last.get("count", 0) >= 2:
        return None  # two ignored reminders per episode; stop is level 3
    stale, n = checkpoint_is_stale(sdir, meta)
    threshold = (min(2, NUDGE_TOOLS) if state_is_template(sdir, meta)
                 else NUDGE_TOOLS)
    if not stale or n < threshold:
        return None
    count = last.get("count", 0) + 1 if ignored else 1
    journal(sdir, "nudge", uncheckpointed=n, count=count)
    meta["last_nudge"] = {"ts": iso(), "uncheckpointed": n, "count": count}
    return render_inject(agent, event,
                         truncate(nudge_text(sdir, meta, n, count),
                                  inject_budget(agent)))


# --- session status / candidates ----------------------------------------------


def session_freshness(meta):
    ts = parse_iso(meta.get("last_event_ts", "")) or 0
    return now_ts() - ts


def classify(sdir, meta):
    """-> (label, stale) where label in active|ended|interrupted."""
    stale, _ = checkpoint_is_stale(sdir, meta)
    if meta.get("status") == "ended":
        return "ended", stale
    if session_freshness(meta) < ACTIVE_MIN * 60:
        return "active", stale
    return "interrupted", stale


def iter_sessions(proj, include_archived=False):
    roots = [os.path.join(proj, "sessions")]
    if include_archived:
        roots.append(os.path.join(proj, "archive"))
    for root in roots:
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            continue
        for entry in entries:
            sdir = os.path.join(root, entry)
            if os.path.isfile(meta_path(sdir)):
                yield sdir, load_meta(sdir)


def resumable_candidates(proj, exclude_key):
    """Sessions worth offering to a new session, newest state first.

    Sessions whose state was adopted by another session are superseded — the
    adopter carries the lineage tip and is offered instead.
    """
    superseded = {m.get("resumed_from") for _, m in iter_sessions(proj)
                  if m.get("resumed_from")}
    out = []
    for sdir, meta in iter_sessions(proj):
        if meta.get("key") == exclude_key:
            continue
        if meta.get("key") in superseded:
            continue
        if state_is_template(sdir, meta):
            continue
        txt = read_text(state_path(sdir))
        if state_status(txt) in ("done", "abandoned"):
            continue
        label, stale = classify(sdir, meta)
        out.append({
            "sdir": sdir, "meta": meta, "label": label, "stale": stale,
            "mtime": state_mtime(sdir) or 0,
            "sections": state_sections(txt),
        })
    out.sort(key=lambda c: c["mtime"], reverse=True)
    return out


def adopted_by(proj, key):
    """Sessions that record resumed_from == key (derived supersede view)."""
    return [m.get("key") for _, m in iter_sessions(proj)
            if m.get("resumed_from") == key]


# --- injection text -----------------------------------------------------------


def script_invocation():
    return "python3 %s" % shlex.quote(os.path.abspath(sys.argv[0]))


def age_str(seconds):
    if seconds < 90:
        return "%ds" % int(seconds)
    if seconds < 5400:
        return "%dm" % int(seconds / 60)
    if seconds < 172800:
        return "%dh" % int(seconds / 3600)
    return "%dd" % int(seconds / 86400)


def rules_text():
    inv = script_invocation()
    return (
        "Rules:\n"
        "- This file is the source of truth for task state — over conversation"
        " history and over any agent-native memory.\n"
        "- Update it immediately after every completed step, decision, plan"
        " change, or failed hypothesis. Rewrite sections in place; do not"
        " append a log. Keep it under ~%d lines.\n"
        "- Set 'Status: done' when the objective is complete.\n"
        "- After any compaction, resume, or gap: re-read it before acting.\n"
        "- To recall prior work in this project: %s search \"<regex>\"\n"
        % (MAX_STATE_LINES, inv))


def concurrency_warnings(proj, meta):
    lines = []
    for sdir, other in iter_sessions(proj):
        if other.get("key") == meta.get("key"):
            continue
        label, _ = classify(sdir, other)
        if label == "active":
            lines.append(
                "CAUTION: session %s (%s) was active %s ago in this project"
                " — it may still be working. Coordinate before touching the"
                " same task." % (other.get("key"), other.get("agent"),
                                 age_str(session_freshness(other))))
    return lines


def compose_session_start(proj, ident, sdir, meta, created, source):
    inv = script_invocation()
    head = ["AGENT WORKING MEMORY (agent-memory, schema %d)" % SCHEMA,
            "You are session %s in project %s." % (meta["key"],
                                                   os.path.basename(proj))]
    if meta.get("worktree") and meta["worktree"] != ident["worktree"]:
        head.append("Note: this session originally ran in worktree %s; you are"
                    " now in %s." % (meta["worktree"], ident["worktree"]))
    head.append("Your working-state file: %s" % state_path(sdir))
    warnings = concurrency_warnings(proj, meta)

    budget = inject_budget(meta.get("agent"))
    if not created and not state_is_template(sdir, meta):
        # resume / compact / clear of a session that already has real state
        stale, n = checkpoint_is_stale(sdir, meta)
        if stale:
            warnings.append(
                "WARNING: this state file may be STALE — %d actions were"
                " journaled after it was last written. Reconcile it with"
                " reality before trusting it." % n)
        body = read_text(state_path(sdir))
        parts = head + [rules_text()] + warnings
        parts.append("--- your current working state (%s) ---" %
                     ("restored after %s" % source if source else "restored"))
        parts.append(truncate(with_breadcrumbs(sdir, meta, body),
                              budget - 1500))
        # The 1500-byte reserve covers head + rules, but concurrency CAUTION
        # lines grow with the number of active sibling sessions — cap the
        # whole message so a busy project can't push codex past its spill.
        return truncate("\n".join(parts), budget)

    # fresh session: offer unfinished work from any agent/worktree
    cands = resumable_candidates(proj, meta["key"])[:CANDIDATES]
    parts = head + [rules_text()] + warnings
    if cands:
        parts.append("Unfinished work found in this project:")
        for i, c in enumerate(cands, 1):
            m = c["meta"]
            flags = c["label"] + (", stale-checkpoint" if c["stale"] else "")
            wt = ""
            if m.get("worktree") and m["worktree"] != ident["worktree"]:
                wt = ", worktree %s" % m["worktree"]
            parts.append(
                "%d. %s (%s, %s ago, %s%s)\n"
                "   Objective: %s\n"
                "   Now: %s\n"
                "   Full state (read-only): %s\n"
                "   To continue it: %s adopt %s --into %s"
                % (i, m.get("key"), m.get("agent"),
                   age_str(now_ts() - c["mtime"]), flags, wt,
                   first_line(c["sections"].get("Objective")) or "(none recorded)",
                   first_line(c["sections"].get("Now (exact stopping point)")) or "(unknown)",
                   state_path(c["sdir"]),
                   inv, m.get("key"), meta["key"]))
        parts.append(
            "If the user's request continues one of these, run the adopt"
            " command FIRST, then re-read your state file. If it is new,"
            " unrelated work, just proceed. Never adopt an 'active' session"
            " without user confirmation.")
        top = cands[0]
        preview = read_text(state_path(top["sdir"]))
        if len(preview) < 4000:
            parts.append("--- most recent candidate (%s), read-only preview ---"
                         % top["meta"].get("key"))
            parts.append(preview)
            # The candidates offer is the one delivery every agent receives
            # on a working channel (Cursor's post-tool inject is dropped
            # upstream), so a crashed session's uncheckpointed tail must
            # surface here or nowhere.
            crumbs = breadcrumb_digest(top["sdir"], top["meta"])
            if crumbs:
                parts.append(crumbs)
    else:
        parts.append("No unfinished work is recorded for this project. Your"
                     " state file starts from the template — fill in Objective"
                     " once the task is clear.")
    # This branch had no overall cap: candidates + preview + breadcrumbs can
    # overrun the per-agent budget even though each piece is bounded.
    return truncate("\n".join(parts), budget)


def breadcrumb_digest(sdir, meta):
    """Journal tail rendered for injection alongside a STALE state file: the
    only freshness a crashed or checkpoint-less session leaves behind. Raw
    evidence, no model cooperation needed. Empty string when fresh."""
    stale, _n = checkpoint_is_stale(sdir, meta)
    if not stale:
        return ""
    tail, total = journal_tool_tail(sdir, state_mtime(sdir))
    if not tail:
        return ""
    lines = ["Uncheckpointed activity since the state file above was last"
             " saved (auto-generated from the tool journal — raw evidence,"
             " not decisions):"]
    for _ts, tool, target in tail:
        lines.append("  - %s %s" % (tool, (target or "")[:120]))
    lines.append("  (%d tool call(s) total; the state file predates all of"
                 " them.) Fold anything still relevant into the state file."
                 % total)
    return "\n".join(lines)


def with_breadcrumbs(sdir, meta, body):
    """body + breadcrumb tail as one string, so a downstream truncate trims
    the breadcrumbs before it ever touches the state body."""
    crumbs = breadcrumb_digest(sdir, meta)
    return body + ("\n\n" + crumbs if crumbs else "")


def compose_reinject(sdir, meta, reason):
    body = read_text(state_path(sdir))
    budget = inject_budget(meta.get("agent"))
    return "\n".join([
        "AGENT WORKING MEMORY — context recovery (%s)." % reason,
        "Your working-state file: %s" % state_path(sdir),
        "Re-read it (and the rules injected at session start) before"
        " continuing. It is the source of truth for task state.",
        "--- current working state ---",
        truncate(with_breadcrumbs(sdir, meta, body), budget - 500),
    ])


# --- event handlers -----------------------------------------------------------


def detect_gap_or_end(meta, prev_last_ts, prev_status):
    """Resume-gap: this session went quiet (or ended) and is talking again."""
    if prev_status == "ended":
        return "resumed after session end"
    if prev_last_ts is None:
        return None
    gap = now_ts() - prev_last_ts
    if gap > GAP_MIN * 60:
        return "resumed after a %s gap" % age_str(gap)
    return None


def take_pending_reinject(meta):
    p = meta.pop("pending_reinject", None)
    return p.get("reason") if isinstance(p, dict) else None


def handle_event(agent, event, norm):
    """Core dispatch. Returns a JSON-serializable output dict or None."""
    sid = norm.get("session_id")
    if not sid:
        return None
    key = session_key(agent, sid)

    # Resolve project: index fast-path, else derive from cwd.
    proj = lookup_project_for(key)
    ident = None
    if proj is None:
        cwd = norm.get("cwd")
        if not cwd or not os.path.isabs(cwd):
            return None  # no way to place this session; stay silent
        proj, ident = ensure_project(cwd)
    if ident is None:
        pj = read_json(os.path.join(proj, "project.json"), {})
        wts = sorted(pj.get("worktrees", {}))
        ident = {"worktree": norm.get("cwd") or (wts[0] if wts else ""),
                 "remote": pj.get("remote")}

    # Same-session hooks can run concurrently (verified: Codex fires
    # SessionStart and UserPromptSubmit simultaneously on the first prompt);
    # serialize the meta read-modify-write so armed flags aren't lost.
    sdir_path = session_dir(proj, key)
    _mkdirs(sdir_path)
    with locked(os.path.join(sdir_path, ".lock")):
        return _handle_locked(agent, event, norm, proj, ident, key)


def _handle_locked(agent, event, norm, proj, ident, key):
    prev_meta = load_meta(session_dir(proj, key))
    prev_last_ts = parse_iso(prev_meta.get("last_event_ts", "")) if prev_meta else None
    prev_status = prev_meta.get("status") if prev_meta else None

    sdir, meta, created = ensure_session(proj, ident, agent,
                                         norm.get("session_id"),
                                         dict(norm, event=event))

    # Generic resume-gap detection (covers agents whose session-start
    # doesn't re-fire on resume, e.g. Cursor).
    if event != "session-start" and not created:
        gap_reason = detect_gap_or_end(meta, prev_last_ts, prev_status)
        if gap_reason and not meta.get("pending_reinject"):
            meta["pending_reinject"] = {"reason": gap_reason, "set_at": iso()}
            journal(sdir, "gap", reason=gap_reason)

    out = None

    if event == "session-start":
        source = norm.get("source") or "startup"
        journal(sdir, "start", source=source, agent_event=True)
        meta.setdefault("sources", []).append({"ts": iso(), "source": source})
        meta["sources"] = meta["sources"][-20:]
        meta.pop("pending_reinject", None)
        meta["last_inject"] = {"ts": iso(), "kind": "session-start"}
        text = compose_session_start(proj, ident, sdir, meta, created, source)
        out = render_inject(agent, event, text)

    elif event == "prompt":
        p = (norm.get("prompt") or "")[:400]
        journal(sdir, "prompt", text=p)
        meta["counts"]["prompts"] = meta.get("counts", {}).get("prompts", 0) + 1
        # A new user turn means the next stop can block again.
        meta.pop("stop_block_pending", None)
        # Only consume the armed re-injection where this event can actually
        # inject (Cursor's beforeSubmitPrompt and Copilot's userPromptSubmitted
        # cannot — the flag must survive them for the next post-tool).
        if (agent, event) in CAN_INJECT:
            reason = take_pending_reinject(meta)
            if reason:
                journal(sdir, "inject", kind="prompt", reason=reason)
                meta["last_inject"] = {"ts": iso(), "kind": "prompt"}
                out = render_inject(agent, event,
                                    compose_reinject(sdir, meta, reason))

    elif event == "post-tool":
        name = norm.get("tool_name") or ""
        target = norm.get("tool_target")
        # The model updating its own state file is the checkpoint itself, not
        # work that makes the checkpoint stale — keep it out of the journal.
        # Separator-anchored so ~/.agent-memory-backup/... is NOT excluded.
        store = store_root().rstrip(os.sep) + os.sep
        touches_store = bool(target) and store in target
        journaled = bool(MUTATING_TOOLS.search(name)) and not touches_store
        if journaled:
            journal(sdir, "tool", tool=name,
                    target=target[:160] if target else None)
            meta["counts"]["tools"] = meta.get("counts", {}).get("tools", 0) + 1
        # Subagent-fired hooks (Claude runs Task-subagent tools under the
        # parent session id) journal their work, but never receive an
        # injection: text delivered here lands in the SUBAGENT's context —
        # a consumed reinject never reaches the parent, and a nudge would
        # tell the subagent to overwrite the parent's checkpoint.
        if (agent, event) in CAN_INJECT and not norm.get("subagent"):
            reason = take_pending_reinject(meta)
            if reason:
                journal(sdir, "inject", kind="post-tool", reason=reason)
                meta["last_inject"] = {"ts": iso(), "kind": "post-tool"}
                out = render_inject(agent, event,
                                    compose_reinject(sdir, meta, reason))
            elif journaled:
                out = maybe_nudge(sdir, meta, agent, event)

    elif event == "stop":
        stale, n = checkpoint_is_stale(sdir, meta)
        journal(sdir, "stop", stale=stale, uncheckpointed=n,
                reason=norm.get("reason"))
        enforce = os.environ.get("AGENT_MEMORY_ENFORCE", "block") != "soft"
        blocked_recently = False
        last_block = parse_iso(meta.get("last_stop_block", ""))
        if last_block is not None and now_ts() - last_block < 30 * 60:
            blocked_recently = True
        # Never force continuation when the USER stopped the agent (Cursor
        # reports status aborted/error; Codex sadly has no such signal).
        user_aborted = (norm.get("reason") or "") in ("aborted", "abort",
                                                      "error", "cancelled")
        if (stale and enforce and not user_aborted
                and not norm.get("stop_hook_active")
                and not blocked_recently):
            meta["last_stop_block"] = iso()
            meta["stop_block_pending"] = True  # cleared at the next clean
            # stop or prompt; while set, nudges must not promise a block
            reason = (
                "agent-memory: your working-state file is stale — %d action(s)"
                " were performed after it was last written. Update %s now so"
                " the task can be resumed by a future session: rewrite"
                " Objective / Done / Now / Next to match reality (set 'Status:"
                " done' if the task is complete). Then finish your reply."
                % (n, state_path(sdir)))
            out = render_stop_block(agent, reason)
        else:
            meta["clean_stop_at"] = iso()
            meta.pop("stop_block_pending", None)

    elif event in ("pre-compact", "post-compact"):
        journal(sdir, "compact", phase=event, trigger=norm.get("trigger"))
        # Claude re-injects via SessionStart(compact); everyone else needs the
        # next inject-capable event to restore state.
        if agent != "claude":
            meta["pending_reinject"] = {"reason": "context compaction",
                                        "set_at": iso()}

    elif event == "session-end":
        meta["status"] = "ended"
        meta["end_reason"] = norm.get("reason") or "unknown"
        meta["ended_at"] = iso()
        stale, n = checkpoint_is_stale(sdir, meta)
        journal(sdir, "end", reason=meta["end_reason"], stale=stale,
                uncheckpointed=n)

    save_meta(sdir, meta)
    return out


# --- subcommands ---------------------------------------------------------------


def cmd_hook(argv):
    if len(argv) < 2 or argv[0] not in AGENTS or argv[1] not in EVENTS:
        log_error("hook: bad args %r" % (argv,))
        return 0
    if os.environ.get("AGENT_MEMORY_DISABLE") == "1":
        return 0
    agent, event = argv[0], argv[1]
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    try:
        norm = ADAPTERS[agent](event, payload)
        out = handle_event(agent, event, norm)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False))
    except Exception as exc:  # never break the host agent
        log_error("hook %s/%s failed: %r" % (agent, event, exc))
    return 0


def _find_session(key_or_prefix, proj=None):
    """Locate a session dir by exact key or unique prefix across projects.

    Multiple entries can share a key (a re-archived session leaves timestamp-
    suffixed copies in archive/): exact matches resolve to the NEWEST one.
    """
    exact, matches = [], []
    proj_list = [proj] if proj else []
    if not proj_list:
        try:
            proj_list = [os.path.join(projects_dir(), d)
                         for d in sorted(os.listdir(projects_dir()))]
        except OSError:
            proj_list = []
    for p in proj_list:
        for sdir, meta in iter_sessions(p, include_archived=True):
            k = meta.get("key", "")
            if k == key_or_prefix:
                exact.append((sdir, meta, p))
            elif k.startswith(key_or_prefix):
                matches.append((sdir, meta, p))
    if exact:
        exact.sort(key=lambda t: parse_iso(t[1].get("last_event_ts", "")) or 0,
                   reverse=True)
        return exact[:1]
    return matches


def cmd_adopt(argv):
    args = list(argv)
    force = "--force" in args
    if force:
        args.remove("--force")
    if "--into" not in args or len(args) < 3:
        print("usage: adopt <source-session> --into <current-session> [--force]")
        return 2
    into_key = args[args.index("--into") + 1]
    src_key = args[0]
    src = _find_session(src_key)
    dst = _find_session(into_key)
    if len(src) != 1:
        print("error: source session %r %s" %
              (src_key, "not found" if not src else "is ambiguous"))
        return 1
    if len(dst) != 1:
        print("error: current session %r %s" %
              (into_key, "not found" if not dst else "is ambiguous"))
        return 1
    src_sdir, src_meta, _ = src[0]
    dst_sdir, dst_meta, _ = dst[0]
    if not state_is_template(dst_sdir, dst_meta) and not force:
        print("error: %s already has non-template state; pass --force to"
              " overwrite it" % dst_meta["key"])
        return 1
    label, _ = classify(src_sdir, src_meta)
    content = read_text(state_path(src_sdir))
    with locked(os.path.join(dst_sdir, ".lock")):
        atomic_write(state_path(dst_sdir), content)
        dst_meta = load_meta(dst_sdir) or dst_meta
        dst_meta["resumed_from"] = src_meta.get("key")
        dst_meta["resumed_at"] = iso()
        save_meta(dst_sdir, dst_meta)
        # Lineage is recorded ONLY in the adopting session (single-writer
        # rule); the source's "adopted_by" view is derived at read time.
        journal(dst_sdir, "adopt", source=src_meta.get("key"))
    print("Adopted state of %s into %s." % (src_meta["key"], dst_meta["key"]))
    if label == "active":
        print("CAUTION: the source session was active %s ago — it may still"
              " be running." % age_str(session_freshness(src_meta)))
    print("State file: %s — re-read it now; reconcile 'Now'/'Next' with"
          " reality before working." % state_path(dst_sdir))
    return 0


def cmd_fresh(argv):
    if "--session" not in argv:
        print("usage: fresh --session <session-key>")
        return 2
    key = argv[argv.index("--session") + 1]
    found = _find_session(key)
    if len(found) != 1:
        print("error: session %r %s" %
              (key, "not found" if not found else "is ambiguous"))
        return 1
    sdir, meta, _ = found[0]
    with locked(os.path.join(sdir, ".lock")):
        if not state_is_template(sdir, meta):
            arch = os.path.join(sdir, "archive")
            _mkdirs(arch)
            dest = os.path.join(arch, "state-%s.md" %
                                iso().replace(":", "").replace("-", ""))
            os.replace(state_path(sdir), dest)
            print("Archived previous state to %s" % dest)
        atomic_write(state_path(sdir), STATE_TEMPLATE)
        meta = load_meta(sdir) or meta
        meta["state_template_sha"] = sha10(STATE_TEMPLATE)
        save_meta(sdir, meta)
        journal(sdir, "fresh")
    print("State file reset to template: %s" % state_path(sdir))
    return 0


def _iter_projects(all_projects, cwd):
    if all_projects:
        try:
            for d in sorted(os.listdir(projects_dir())):
                yield os.path.join(projects_dir(), d)
        except OSError:
            return
    else:
        ident = project_identity(cwd)
        proj = find_project_dir(ident)
        if os.path.isdir(proj):
            yield proj


def cmd_status(argv):
    all_p = "--all-projects" in argv
    as_json = "--json" in argv
    rows = []
    for proj in _iter_projects(all_p, os.getcwd()):
        pj = read_json(os.path.join(proj, "project.json"), {})
        for sdir, meta in iter_sessions(proj):
            label, stale = classify(sdir, meta)
            txt = read_text(state_path(sdir))
            rows.append({
                "project": os.path.basename(proj),
                "identity": pj.get("identity", {}),
                "key": meta.get("key"),
                "agent": meta.get("agent"),
                "status": label,
                "state_status": state_status(txt),
                "stale_checkpoint": stale,
                "last_event": meta.get("last_event_ts"),
                "age": age_str(session_freshness(meta)),
                "worktree": meta.get("worktree"),
                "objective": first_line(state_sections(txt).get("Objective")),
                "state_path": state_path(sdir),
                "resumed_from": meta.get("resumed_from"),
                "end_reason": meta.get("end_reason"),
            })
    if as_json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("no sessions recorded%s" % ("" if all_p else " for this project"))
        return 0
    cur_proj = None
    for r in rows:
        if r["project"] != cur_proj:
            cur_proj = r["project"]
            ident = r["identity"]
            print("project %s  (%s: %s)" % (cur_proj, ident.get("kind", "?"),
                                            str(ident.get("key", "?"))[:60]))
        flags = r["status"] + (" STALE" if r["stale_checkpoint"] else "")
        if r["state_status"] != "in-progress":
            flags += " [%s]" % r["state_status"]
        print("  %-44s %-10s %-6s %s" % (r["key"], flags, r["age"],
                                         r["objective"] or "-"))
    return 0


def cmd_search(argv):
    args = [a for a in argv]
    all_p = "--all-projects" in args
    if all_p:
        args.remove("--all-projects")
    limit = 20
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print("usage: search <regex> [--all-projects] [--limit N]")
        return 2
    try:
        pat = re.compile(args[0], re.IGNORECASE)
    except re.error as e:
        print("error: bad regex: %s" % e)
        return 2
    hits = []
    for proj in _iter_projects(all_p, os.getcwd()):
        for sdir, meta in iter_sessions(proj, include_archived=True):
            prov = "%s/%s" % (os.path.basename(proj), meta.get("key"))
            files = [state_path(sdir), journal_path(sdir),
                     journal_path(sdir) + ".1"]
            arch = os.path.join(sdir, "archive")
            try:
                files += [os.path.join(arch, f) for f in sorted(os.listdir(arch))]
            except OSError:
                pass
            for path in files:
                for ln, line in enumerate(read_text(path).splitlines(), 1):
                    if pat.search(line):
                        hits.append((meta.get("last_event_ts", ""), prov,
                                     os.path.basename(path), ln, line.strip()))
    hits.sort(reverse=True)
    for ts, prov, fname, ln, line in hits[:limit]:
        print("%s  %s  %s:%d\n    %s" % (ts or "-", prov, fname, ln, line[:200]))
    if not hits:
        print("no matches (searched agent-memory store%s). For raw transcript"
              " history, see each agent's native store or the brain-dump"
              " skill." % ("" if not all_p else ", all projects"))
    return 0 if hits else 1


def cmd_show(argv):
    if not argv:
        print("usage: show <session-key-or-prefix>")
        return 2
    found = _find_session(argv[0])
    if len(found) != 1:
        print("error: session %r %s" %
              (argv[0], "not found" if not found else "is ambiguous"))
        return 1
    sdir, meta, proj = found[0]
    label, stale = classify(sdir, meta)
    print("session %s  (%s, %s%s)" % (meta.get("key"), label,
                                      "stale checkpoint, " if stale else "",
                                      "project " + os.path.basename(proj)))
    for k in ("agent", "session_id", "created_at", "last_event_ts", "status",
              "end_reason", "worktree", "cwd_last", "transcript_path",
              "resumed_from"):
        if meta.get(k):
            print("  %-16s %s" % (k, meta[k]))
    others = adopted_by(proj, meta.get("key"))
    if others:
        print("  %-16s %s" % ("adopted_by", ", ".join(filter(None, others))))
    print("--- state.md ---")
    print(read_text(state_path(sdir)) or "(missing)")
    tail = journal_text(sdir).splitlines()[-15:]
    print("--- journal (last %d) ---" % len(tail))
    for line in tail:
        print(line)
    return 0


def cmd_prune(argv):
    days = 30
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])
    cutoff = now_ts() - days * 86400
    moved = 0
    for proj in _iter_projects(True, os.getcwd()):
        for sdir, meta in list(iter_sessions(proj)):
            # Take the session lock and re-read: a session resumed between
            # the scan and the move must not be archived out from under its
            # hooks (skip on lock contention — an active hook holds it).
            with locked(os.path.join(sdir, ".lock"), timeout=0.2) as got:
                if not got:
                    continue
                meta = load_meta(sdir)
                ts = parse_iso(meta.get("last_event_ts", "")) or 0
                if meta.get("status") != "ended" or ts >= cutoff:
                    continue
                arch = os.path.join(proj, "archive")
                _mkdirs(arch)
                dest = os.path.join(arch, os.path.basename(sdir))
                if os.path.exists(dest):  # same key archived before
                    dest += "-" + iso().replace(":", "")
                os.replace(sdir, dest)
                try:
                    os.remove(index_path(meta.get("key", "")))
                except OSError:
                    pass
                moved += 1
    print("archived %d ended session(s) older than %d days" % (moved, days))
    return 0


# --- doctor ---------------------------------------------------------------------


def _version_here():
    here = os.path.dirname(os.path.realpath(__file__))
    return read_text(os.path.join(here, "VERSION")).strip() or "unknown"


def _check(results, agent, level, msg):
    results.append({"agent": agent, "level": level, "msg": msg})


def _doctor_agent(results, agent, home):
    hook_py = os.path.join(home, ".%s" % agent, "hooks", "agent-memory.py")
    cli = {"claude": "claude", "codex": "codex", "cursor": "cursor-agent",
           "copilot": "copilot"}[agent]
    from shutil import which
    if not which(cli):
        _check(results, agent, "info", "`%s` not on PATH — hooks are staged"
               " but dormant on this host" % cli)
    if not os.path.exists(hook_py):
        _check(results, agent, "fail", "adapter %s missing — run the installer"
               % hook_py)
        return
    my_src = read_text(os.path.realpath(__file__))
    their_src = read_text(os.path.realpath(hook_py))
    if my_src != their_src:
        _check(results, agent, "fail", "installed %s differs from this script"
               " — version drift; re-run the installer" % hook_py)

    if agent == "claude":
        cfg = read_json(os.path.join(home, ".claude", "settings.json"), {})
        hooks = cfg.get("hooks", {}) if isinstance(cfg, dict) else {}
        txt = json.dumps(hooks)
        for ev in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop",
                   "PreCompact", "SessionEnd"):
            if ev not in hooks or "agent-memory" not in json.dumps(hooks.get(ev, [])):
                _check(results, agent, "fail",
                       "settings.json: %s not registered for agent-memory" % ev)
        if "session-scratchpad" in txt:
            _check(results, agent, "warn", "legacy session-scratchpad hook is"
                   " still registered in settings.json — remove it (competing"
                   " authority)")
        allow = json.dumps(cfg.get("permissions", {}))
        if ".agent-memory" not in allow:
            _check(results, agent, "warn", "settings.json permissions do not"
                   " allow ~/.agent-memory/** — Claude will prompt before"
                   " editing its state file")
        md = read_text(os.path.join(home, ".claude", "CLAUDE.md"))
        if "## Agent working memory" not in md:
            _check(results, agent, "warn", "~/.claude/CLAUDE.md lacks the"
                   " durable ingest section")
    elif agent == "codex":
        toml = read_text(os.path.join(home, ".codex", "config.toml"))
        for ev in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop",
                   "PreCompact", "PostCompact"):
            if ("[[hooks.%s]]" % ev) not in toml or "agent-memory" not in toml:
                _check(results, agent, "fail",
                       "config.toml: hooks.%s not registered" % ev)
        if "session-scratchpad" in toml:
            _check(results, agent, "warn", "legacy session-scratchpad hook"
                   " still in config.toml — remove it")
        if "trusted_hash" not in toml:
            _check(results, agent, "warn", "no [hooks.state] trust entries in"
                   " config.toml — Codex SILENTLY SKIPS untrusted hooks in"
                   " headless runs; open the codex TUI once and trust the"
                   " hooks")
        hooks_json = os.path.join(home, ".codex", "hooks.json")
        if os.path.exists(hooks_json) and "agent-memory" in read_text(hooks_json):
            _check(results, agent, "warn", "agent-memory also registered in"
                   " ~/.codex/hooks.json — codex honors BOTH files, hooks"
                   " would run twice")
        md = read_text(os.path.join(home, ".codex", "AGENTS.md"))
        if "## Agent working memory" not in md:
            _check(results, agent, "warn", "~/.codex/AGENTS.md lacks the"
                   " durable ingest section (the only channel that survives"
                   " codex compaction)")
    elif agent == "cursor":
        cfg = read_json(os.path.join(home, ".cursor", "hooks.json"), {})
        hooks = cfg.get("hooks", {}) if isinstance(cfg, dict) else {}
        for ev in ("sessionStart", "beforeSubmitPrompt", "postToolUse", "stop",
                   "preCompact", "sessionEnd"):
            cmds = json.dumps(hooks.get(ev, []))
            if "agent-memory" not in cmds:
                _check(results, agent, "fail",
                       "hooks.json: %s not registered" % ev)
        if "session-scratchpad" in json.dumps(hooks):
            _check(results, agent, "warn", "legacy session-scratchpad hook"
                   " still in hooks.json — remove it")
        wrap_dir = os.path.join(home, ".cursor", "hooks", "agent-memory")
        for ev in ("session-start", "prompt", "post-tool", "stop",
                   "pre-compact", "session-end"):
            w = os.path.join(wrap_dir, ev + ".sh")
            if not (os.path.isfile(w) and os.access(w, os.X_OK)):
                _check(results, agent, "fail", "wrapper %s missing or not"
                       " executable" % w)
    elif agent == "copilot":
        cfg = read_json(os.path.join(home, ".copilot", "hooks",
                                     "agent-memory.json"), {})
        hooks = cfg.get("hooks", {}) if isinstance(cfg, dict) else {}
        for ev in ("sessionStart", "userPromptSubmitted", "postToolUse",
                   "agentStop", "preCompact", "sessionEnd"):
            if ev not in hooks:
                _check(results, agent, "fail",
                       "hooks/agent-memory.json: %s not registered" % ev)
        legacy = os.path.join(home, ".copilot", "hooks",
                              "session-scratchpad.json")
        if os.path.exists(legacy):
            _check(results, agent, "warn", "legacy %s still present — remove"
                   " it" % legacy)
        md = read_text(os.path.join(home, ".copilot",
                                    "copilot-instructions.md"))
        if "## Agent working memory" not in md:
            _check(results, agent, "warn", "~/.copilot/copilot-instructions.md"
                   " lacks the durable ingest section (needed to survive"
                   " copilot compaction)")


def cmd_doctor(argv):
    as_json = "--json" in argv
    home = os.path.expanduser("~")
    results = []
    # store health
    root = store_root()
    try:
        _mkdirs(root)
        probe = os.path.join(root, ".probe")
        atomic_write(probe, "ok")
        os.remove(probe)
        _check(results, "store", "pass", "store writable at %s" % root)
    except OSError as e:
        _check(results, "store", "fail", "store not writable: %s" % e)
    sj = os.path.join(root, "store.json")
    stored = read_json(sj, None)
    if stored is None:
        try:
            write_json(sj, {"schema": SCHEMA, "created_at": iso()})
        except OSError:
            pass  # already reported as not-writable above
    elif stored.get("schema", SCHEMA) > SCHEMA:
        _check(results, "store", "fail", "store schema %s is newer than this"
               " script (%s) — update the repo clone" %
               (stored.get("schema"), SCHEMA))
    _check(results, "store", "pass", "agent-memory version %s" % _version_here())
    for legacy in ("claude", "codex", "cursor", "copilot"):
        old = os.path.join(home, ".%s-session-scratchpads" % legacy)
        if os.path.isdir(old):
            _check(results, "store", "info", "legacy scratchpad store %s"
                   " exists — not migrated; consult it manually if old state"
                   " matters" % old)
    for agent in AGENTS:
        try:
            _doctor_agent(results, agent, home)
        except Exception as exc:
            _check(results, agent, "fail", "doctor check crashed: %r" % exc)
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print("[%s] %-7s %s" % (r["level"].upper(), r["agent"], r["msg"]))
    worst = {"pass": 0, "info": 0, "warn": 1, "fail": 2}
    code = max(worst.get(r["level"], 0) for r in results) if results else 0
    if not as_json:
        print("doctor: %s" % ("OK" if code == 0 else
                              "WARNINGS" if code == 1 else "FAILURES"))
    return 0 if code < 2 else 1


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "hook":
        return cmd_hook(rest)
    if cmd == "version":
        print(_version_here())
        return 0
    cmds = {"adopt": cmd_adopt, "fresh": cmd_fresh, "status": cmd_status,
            "search": cmd_search, "show": cmd_show, "prune": cmd_prune,
            "doctor": cmd_doctor}
    if cmd not in cmds:
        print("unknown command %r\n%s" % (cmd, __doc__))
        return 2
    try:
        return cmds[cmd](rest)
    except (IndexError, ValueError) as exc:
        print("error: bad arguments for %r (%s)" % (cmd, exc))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

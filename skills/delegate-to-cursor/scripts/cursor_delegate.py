#!/usr/bin/env python3
"""Delegate an implementation task to the Cursor CLI (`cursor-agent`) and audit
what it actually did.

Three subcommands:

  run        preflight, snapshot the tree, invoke cursor-agent, print a summary
  summarize  condense an existing run.jsonl (for runs launched separately)
  verify     diff the tree against the snapshot and flag claim/reality mismatch

The flag set in `run` is not adjustable, because each part of it was established
by testing the CLI rather than reading its help:

  --print --output-format stream-json   one JSON event per line; flushed
                                        incrementally, so a killed run is still
                                        auditable
  --trust                               without it an unfamiliar workspace exits
                                        1 with a trust prompt and no JSON
  --force                               without it the shell tool is blocked
                                        outright, the run still exits 0 with
                                        is_error=false, and the model reports
                                        command output it never ran

The prompt goes in on stdin, which sidesteps argv length and quoting limits.

`cursor-agent` has no timeout flag and this repo cannot assume a `timeout(1)`
binary, so the cap here is a Python one: the child gets its own session and the
process group is signalled on expiry.

Event shapes consumed by `summarize` (type=tool_call): the `tool_call` object
holds `toolCallId`, `startedAtMs`, `completedAtMs`, `hookAdditionalContexts`,
and exactly one `<name>ToolCall` dict of `{args, result}`. A result is
`{"success": {...}}` or `{"failure": {...}}`; for shells both carry `command`,
`workingDirectory`, `exitCode`, `stdout`, `stderr`.
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "cursor-grok-4.6-high"
DEFAULT_TIMEOUT = 900
DEFAULT_MAX_CHARS = 4000
MAX_LISTED = 40
GRACE_SECONDS = 3
PREFLIGHT_TIMEOUT = 60
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# Every delegated run touches these: the agent-memory hooks write a working-state
# file, and cursor-agent keeps its own session state. Counting them as strays
# would flag a mismatch on every single run.
HOUSEKEEPING = ("/.agent-memory/", "/.cursor/", "/.codex/", "/.claude/")


def housekeeping(path):
    return any(part in path for part in HOUSEKEEPING)


def die(msg, code=2):
    print("delegate-to-cursor: " + msg, file=sys.stderr)
    raise SystemExit(code)


def git(cwd, *args, check=True):
    try:
        p = subprocess.run(["git", "-C", str(cwd), *args],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        if check:
            die("git %s failed: %s" % (" ".join(args), exc))
        return None
    if p.returncode != 0:
        if check:
            die("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
        return None
    return p.stdout


def clean(text, limit=None):
    text = ANSI_RE.sub("", text or "").strip()
    if limit and len(text) > limit:
        text = text[:limit] + " …[truncated]"
    return text


# ---------------------------------------------------------------- preflight

def preflight(model, cwd):
    exe = shutil.which("cursor-agent")
    if not exe:
        die("cursor-agent is not on PATH. Install the Cursor CLI, or run the "
            "task yourself instead of delegating it.")
    if not cwd.is_dir():
        die("--cwd %s is not a directory" % cwd)
    if git(cwd, "rev-parse", "--git-dir", check=False) is None:
        die("--cwd %s is not a git repository. Delegation edits in place, so "
            "git is the only way to see what changed." % cwd)

    try:
        status = subprocess.run([exe, "status"], capture_output=True, text=True,
                                timeout=PREFLIGHT_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        die("could not run `cursor-agent status`: %s" % exc)
    if status.returncode != 0 or "Logged in" not in status.stdout:
        die("cursor-agent is not authenticated — run `cursor-agent login`.\n"
            + clean(status.stdout + status.stderr, 400))

    try:
        listing = subprocess.run([exe, "--list-models"], capture_output=True,
                                 text=True, timeout=PREFLIGHT_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        die("could not run `cursor-agent --list-models`: %s" % exc)
    models = {ln.split(" - ")[0].strip()
              for ln in clean(listing.stdout).splitlines() if " - " in ln}
    if models and model not in models:
        die("unknown model %r. Run `cursor-agent --list-models` — ids drift "
            "between CLI releases." % model)
    return exe


# ---------------------------------------------------------------- snapshot

def snapshot(cwd):
    head = clean(git(cwd, "rev-parse", "HEAD", check=False) or "")
    porcelain = git(cwd, "status", "--porcelain", check=False) or ""
    return {
        "cwd": str(cwd.resolve()),
        "head": head or None,
        "porcelain": sorted(ln for ln in porcelain.splitlines() if ln.strip()),
        "recorded_at": time.time(),
    }


def load_baseline(out_dir):
    path = out_dir / "baseline.json"
    if not path.exists():
        die("no baseline.json in %s — it is written by `run`, so verify can "
            "only be used on a directory that `run` created." % out_dir)
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        die("could not read %s: %s" % (path, exc))


# ---------------------------------------------------------------- liveness

def write_state(out_dir, **fields):
    path = out_dir / "run.state"
    state = {}
    if path.exists():
        try:
            state = json.loads(path.read_text())
        except (OSError, ValueError):
            state = {}
    state.update(fields)
    try:
        path.write_text(json.dumps(state, indent=1))
    except OSError:
        pass
    return state


def read_state(out_dir):
    path = Path(out_dir) / "run.state"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def running(out_dir):
    """True while the delegated run is still going.

    Without this a partial log is indistinguishable from a dead one, and the
    summary would report a healthy in-flight run as having died.
    """
    state = read_state(out_dir)
    return alive(state.get("pid")) and not state.get("ended_at")


# ---------------------------------------------------------------- parsing

def events(path):
    try:
        handle = open(path, errors="replace")
    except OSError as exc:
        die("could not read %s: %s" % (path, exc))
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def tool_calls(path):
    """Yield (name, args, result) for each completed tool call, in order."""
    for event in events(path):
        if event.get("type") != "tool_call" or event.get("subtype") != "completed":
            continue
        for name, body in (event.get("tool_call") or {}).items():
            if not name.endswith("ToolCall") or not isinstance(body, dict):
                continue
            yield name, body.get("args") or {}, body.get("result")


KINDS = {"success": "success", "failure": "failure", "error": "failure",
         "rejected": "blocked"}


def outcome(result):
    """('success'|'failure'|'blocked'|'unknown', payload).

    Results are single-key maps. `rejected` is the one that matters most: the
    CLI refused to run the command, which is what happens to everything outside
    the allowlist when --force is missing.
    """
    if not isinstance(result, dict):
        return "unknown", {}
    for key, kind in KINDS.items():
        if key in result:
            payload = result[key]
            return kind, payload if isinstance(payload, dict) else {}
    return "unknown", {}


def final_result(path):
    for event in reversed(list(events(path))):
        if event.get("type") == "result":
            return event
    return None


def digest(path, cwd=None, max_chars=DEFAULT_MAX_CHARS):
    edits, chores, reads, shells = [], [], 0, []
    for name, args, result in tool_calls(path):
        if name == "editToolCall":
            target = args.get("path")
            if not target:
                continue
            bucket = chores if housekeeping(target) else edits
            if target not in bucket:
                bucket.append(target)
        elif name == "readToolCall":
            reads += 1
        elif name == "shellToolCall":
            kind, payload = outcome(result)
            shells.append({
                "command": (args.get("command") if args else None)
                           or payload.get("command") or "",
                "kind": kind,
                "exit": payload.get("exitCode"),
                "wd": payload.get("workingDirectory") or "",
                "stdout": clean(payload.get("stdout"), 300),
                "stderr": clean(payload.get("stderr"), 300),
            })

    resolved = str(Path(cwd).resolve()) if cwd else None
    stray = sorted({s["wd"] for s in shells if s["wd"] and resolved
                    and not s["wd"].startswith(resolved)
                    and not housekeeping(s["wd"])})
    outside = [p for p in edits if resolved and not p.startswith(resolved)]

    return {
        "final": final_result(path),
        "edits": edits,
        "edits_outside_cwd": outside,
        "housekeeping_edits": chores,
        "reads": reads,
        "shells": shells,
        "shells_failed": [s for s in shells if s["kind"] == "failure"],
        "shells_blocked": [s for s in shells if s["kind"] == "blocked"],
        "stray_working_dirs": stray,
        "max_chars": max_chars,
    }


# ---------------------------------------------------------------- reporting

def shortlist(shells):
    """Every command when the list is short. Otherwise every failed or blocked
    one plus the most recent successes, in the order they ran — a red run
    followed by a green one is the evidence, so neither half can be dropped.
    """
    if len(shells) <= MAX_LISTED:
        return shells
    keep = {i for i, s in enumerate(shells) if s["kind"] != "success"}
    budget = MAX_LISTED - len(keep)
    for i in reversed(range(len(shells))):
        if budget <= 0:
            break
        if i not in keep:
            keep.add(i)
            budget -= 1
    return [s for i, s in enumerate(shells) if i in sorted(keep)[:MAX_LISTED]]


def render(d, cwd=None, live=False):
    out = []
    final = d["final"] or {}
    usage = final.get("usage") or {}
    if final:
        out.append("status: %s (is_error=%s) api=%ss" % (
            final.get("subtype"), final.get("is_error"),
            round((final.get("duration_api_ms") or 0) / 1000, 1)))
        out.append("session: %s   (resume with --resume %s)"
                   % (final.get("session_id"), final.get("session_id")))
        out.append("tokens: in=%s out=%s cache_read=%s" % (
            usage.get("inputTokens"), usage.get("outputTokens"),
            usage.get("cacheReadTokens")))
    elif live:
        out.append("status: IN PROGRESS — no result event yet. Everything below "
                   "is a partial view of a run that is still going.")
    else:
        out.append("status: NO RESULT EVENT — the run was killed or died before "
                   "finishing. Its partial edits are still on disk.")

    out.append("")
    out.append("files written via the edit tool (%d) — a delegate that uses "
               "shell redirection instead will show up below:" % len(d["edits"]))
    for path in d["edits"][:MAX_LISTED]:
        rel = path
        if cwd:
            try:
                rel = str(Path(path).relative_to(Path(cwd).resolve()))
            except ValueError:
                rel = path
        out.append("  %s" % rel)
    if len(d["edits"]) > MAX_LISTED:
        out.append("  … and %d more" % (len(d["edits"]) - MAX_LISTED))
    if not d["edits"]:
        out.append("  (none)")
    if d["housekeeping_edits"]:
        out.append("  (+%d agent-memory/session-state file(s), not your change)"
                   % len(d["housekeeping_edits"]))

    out.append("")
    out.append("shell commands (%d attempted, %d failed, %d blocked):"
               % (len(d["shells"]), len(d["shells_failed"]),
                  len(d["shells_blocked"])))
    marks = {"success": "ok     ", "failure": "FAIL   ", "blocked": "BLOCKED"}
    for s in shortlist(d["shells"]):
        mark = marks.get(s["kind"], "unknown")
        detail = "" if s["kind"] == "blocked" else " exit=%s" % s["exit"]
        out.append("  [%s%s] %s" % (mark, detail, clean(s["command"], 160)))
        if s["kind"] == "failure" and s["stderr"]:
            out.append("        stderr: %s" % s["stderr"].replace("\n", " ⏎ "))
    hidden = len(d["shells"]) - len(shortlist(d["shells"]))
    if hidden:
        out.append("  (%d more, omitted)" % hidden)
    if not d["shells"]:
        out.append("  (none) — nothing was executed, so no claim in the report "
                   "below is backed by a command.")
    if d["shells_blocked"]:
        out.append("  %d command(s) were refused by the CLI. Anything the "
                   "report says about their output is unbacked."
                   % len(d["shells_blocked"]))

    if d["stray_working_dirs"]:
        out.append("")
        out.append("WARNING: shell commands ran outside the target directory:")
        for wd in d["stray_working_dirs"]:
            out.append("  %s" % wd)
    if d["edits_outside_cwd"]:
        out.append("")
        out.append("WARNING: edits landed outside the target directory:")
        for path in d["edits_outside_cwd"]:
            out.append("  %s" % path)

    out.append("")
    out.append("delegate's own report (treat as a claim, not evidence):")
    out.append(clean(final.get("result"), d["max_chars"]) or "  (none)")
    return "\n".join(out)


# ---------------------------------------------------------------- verify

def changed_paths(cwd, baseline):
    before = set(baseline.get("porcelain") or [])
    now = git(cwd, "status", "--porcelain", check=False) or ""
    after = {ln for ln in now.splitlines() if ln.strip()}
    return sorted(after - before), sorted(before - after)


def do_verify(out_dir, max_chars):
    if running(out_dir):
        print("STILL RUNNING: this run has not finished, so nothing here is "
              "final. Wait for it, then verify. `status --out %s` shows "
              "progress." % out_dir)
        return 1
    baseline = load_baseline(out_dir)
    cwd = Path(baseline["cwd"])
    if not cwd.is_dir():
        die("the recorded working directory %s no longer exists" % cwd)

    new, gone = changed_paths(cwd, baseline)
    head = clean(git(cwd, "rev-parse", "HEAD", check=False) or "") or None
    log = out_dir / "run.jsonl"
    d = digest(log, cwd, max_chars) if log.exists() else None
    state = read_state(out_dir)

    print("baseline HEAD: %s" % (baseline.get("head") or "(no commits)"))
    if head != baseline.get("head"):
        print("HEAD MOVED: now %s — the delegate committed or reset. Review "
              "`git log` before trusting the diff." % (head or "(none)"))

    print("")
    print("working tree changes since baseline (%d):" % len(new))
    for entry in new[:MAX_LISTED]:
        print("  %s" % entry)
    if len(new) > MAX_LISTED:
        print("  … and %d more" % (len(new) - MAX_LISTED))
    if gone:
        print("entries that disappeared from the baseline status (%d):" % len(gone))
        for entry in gone:
            print("  %s" % entry)
    stat = clean(git(cwd, "diff", "--stat", check=False) or "")
    if stat:
        print("")
        print("git diff --stat:")
        print(stat)

    if d is None:
        print("")
        print("no run.jsonl in %s — cannot cross-check the delegate's claims." % out_dir)
        return 1 if not new else 0

    final = d["final"] or {}
    claimed = bool(final) and final.get("is_error") is False
    if state.get("outcome") == "timeout":
        print("")
        print("TIMED OUT: the run was killed at its %ss cap. The changes above "
              "are whatever it had finished by then — treat them as partial "
              "work, not a delivered change." % state.get("timeout"))
        return 1
    print("")
    if claimed and not new and head == baseline.get("head"):
        print("CLAIM/REALITY MISMATCH: the delegate reported success and the "
              "tree is unchanged. Nothing was done. Do not report this as "
              "completed work.")
        return 1
    if d["shells_blocked"]:
        print("CLAIM/REALITY MISMATCH: %d command(s) were refused by the CLI, so "
              "the delegate could not run its own checks — including anything it "
              "claims to have verified. This is what a missing --force looks "
              "like. Re-run the oracle yourself before keeping the diff."
              % len(d["shells_blocked"]))
        return 1
    if claimed and d["shells_failed"] and len(d["shells_failed"]) == len(d["shells"]):
        print("CLAIM/REALITY MISMATCH: the delegate reported success but every "
              "command it ran failed. Any verification it describes is invented.")
        return 1
    if d["stray_working_dirs"] or d["edits_outside_cwd"]:
        print("CLAIM/REALITY MISMATCH: the delegate worked outside %s, so its "
              "changes are not in this tree." % cwd)
        return 1
    if not claimed:
        print("The delegate did not report success. Read the summary before "
              "deciding whether to keep the partial changes above.")
        return 1
    print("No mismatch detected. This says the delegate really edited these "
          "files — not that the change is correct. Re-run the oracle yourself.")
    return 0


# ---------------------------------------------------------------- status

def do_status(out_dir, max_chars):
    """Progress on a run that may still be going — safe to poll."""
    state = read_state(out_dir)
    log = out_dir / "run.jsonl"
    if not state and not log.exists():
        die("no run in %s — status needs a directory that `run` created." % out_dir)

    live = running(out_dir)
    started = state.get("started_at")
    elapsed = round((state.get("ended_at") or time.time()) - started) if started else None

    if live:
        head = "RUNNING (pid %s" % state.get("pid")
        if elapsed is not None:
            head += ", %ss elapsed" % elapsed
        if state.get("timeout"):
            head += " of %ss" % state["timeout"]
        print(head + ")")
    elif state.get("outcome") == "timeout":
        print("TIMED OUT and was killed at its %ss cap." % state.get("timeout"))
    elif state.get("outcome"):
        print("FINISHED%s." % (" in %ss" % elapsed if elapsed is not None else ""))
    else:
        print("NOT RUNNING (no completion recorded — it may have been killed "
              "with its wrapper).")

    if not log.exists():
        print("no output yet.")
        return 0 if live else 1

    d = digest(log, state.get("cwd"), max_chars)
    print("progress: %d edit(s), %d shell command(s) (%d failed, %d blocked), "
          "%d read(s)" % (len(d["edits"]), len(d["shells"]),
                          len(d["shells_failed"]), len(d["shells_blocked"]),
                          d["reads"]))
    if d["shells"]:
        last = d["shells"][-1]
        print("latest command: [%s] %s" % (last["kind"], clean(last["command"], 120)))
    if d["edits"]:
        print("latest edit: %s" % d["edits"][-1])
    if live:
        print("Not final. Do not verify or report until this says FINISHED.")
    return 0


# ---------------------------------------------------------------- run

def do_run(args):
    cwd = Path(args.cwd).expanduser()
    exe = preflight(args.model, cwd)

    if args.brief == "-":
        brief = sys.stdin.read()
    else:
        try:
            brief = Path(args.brief).expanduser().read_text()
        except OSError as exc:
            die("could not read brief %s: %s" % (args.brief, exc))
    if not brief.strip():
        die("the brief is empty")

    out_dir = Path(args.out).expanduser() if args.out else Path(
        "/tmp/delegate-to-cursor-%d" % int(time.time()))
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        die("could not create %s: %s" % (out_dir, exc))

    (out_dir / "brief.md").write_text(brief)
    (out_dir / "baseline.json").write_text(json.dumps(snapshot(cwd), indent=1))

    cmd = [exe, "--print", "--output-format", "stream-json", "--trust",
           "--force", "--model", args.model]
    if args.read_only:
        cmd += ["--mode", "plan"]
    if args.resume:
        cmd += ["--resume", args.resume]
    (out_dir / "command.txt").write_text(" ".join(cmd) + "\n")

    log_path = out_dir / "run.jsonl"
    print("delegating to %s in %s (timeout %ds)" % (args.model, cwd, args.timeout),
          file=sys.stderr)
    print("run dir: %s" % out_dir, file=sys.stderr)

    print("watch it with: python3 %s status --out %s"
          % (Path(__file__).name, out_dir), file=sys.stderr)

    killed = False
    with open(log_path, "wb") as log:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log,
                                    stderr=subprocess.STDOUT, cwd=str(cwd),
                                    start_new_session=True)
        except OSError as exc:
            die("could not start cursor-agent: %s" % exc)
        write_state(out_dir, pid=proc.pid, started_at=time.time(),
                    timeout=args.timeout, model=args.model, cwd=str(cwd),
                    ended_at=None, outcome=None)
        try:
            proc.communicate(brief.encode(), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            killed = True
            terminate(proc)
            proc.communicate()
        except KeyboardInterrupt:
            killed = True
            terminate(proc)
            proc.communicate()
            raise
        finally:
            write_state(out_dir, pid=None, ended_at=time.time(),
                        outcome="timeout" if killed else "finished")

    d = digest(log_path, cwd, args.max_chars)
    if killed:
        print("TIMED OUT after %ds and was killed. Partial edits are on disk; "
              "the log below covers what it managed to do." % args.timeout,
              file=sys.stderr)
    print(render(d, cwd))
    print("")
    print("run dir: %s" % out_dir)
    print("verify with: python3 %s verify --out %s" % (Path(__file__).name, out_dir))

    final = d["final"] or {}
    if killed or not final or final.get("is_error") is not False:
        return 1
    return 0


def terminate(proc):
    try:
        group = os.getpgid(proc.pid)
    except OSError:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(group, sig)
        except OSError:
            return
        deadline = time.time() + GRACE_SECONDS
        while time.time() < deadline:
            if proc.poll() is not None:
                return
            time.sleep(0.2)


# ---------------------------------------------------------------- cli

def main():
    parser = argparse.ArgumentParser(
        prog="cursor_delegate.py",
        description="Delegate an implementation task to cursor-agent and audit it.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="invoke cursor-agent on a brief")
    run.add_argument("--brief", required=True,
                     help="path to the brief, or - to read it from stdin")
    run.add_argument("--model", default=DEFAULT_MODEL,
                     help="default %(default)s; use cursor-grok-4.6-xhigh for "
                          "complex work")
    run.add_argument("--cwd", default=".", help="repository to work in")
    run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                     help="wall-clock cap in seconds (default %(default)s)")
    run.add_argument("--resume", metavar="SESSION_ID",
                     help="continue an earlier run with its context intact")
    run.add_argument("--out", help="run directory (default /tmp/delegate-to-cursor-<ts>)")
    run.add_argument("--read-only", action="store_true",
                     help="plan mode — for review delegations, not implementation")
    run.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)

    summarize = sub.add_parser("summarize", help="condense an existing run.jsonl")
    summarize.add_argument("log", help="path to run.jsonl")
    summarize.add_argument("--cwd", help="repository the run targeted")
    summarize.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    summarize.add_argument("--json", action="store_true",
                           help="emit the digest as JSON")

    status = sub.add_parser("status",
                            help="progress of a run, safe to poll while it runs")
    status.add_argument("--out", required=True, help="run directory from `run`")
    status.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)

    verify = sub.add_parser("verify", help="check the tree against the baseline")
    verify.add_argument("--out", required=True, help="run directory from `run`")
    verify.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)

    args = parser.parse_args()
    if args.command == "run":
        return do_run(args)
    if args.command == "summarize":
        log = Path(args.log).expanduser()
        d = digest(log, args.cwd, args.max_chars)
        if args.json:
            print(json.dumps(d, indent=1, default=str))
        else:
            print(render(d, args.cwd, live=running(log.parent)))
        return 0
    if args.command == "status":
        return do_status(Path(args.out).expanduser(), args.max_chars)
    return do_verify(Path(args.out).expanduser(), args.max_chars)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)

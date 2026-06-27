#!/usr/bin/env python3
"""Condense a Cursor, Claude Code, Codex, or Copilot CLI agent transcript into
a compact, turn-by-turn summary.

The transcript format is auto-detected per file: top-level `role` => Cursor;
a `payload` envelope (`session_meta`/`response_item`/`event_msg`) => Codex; a
dotted `type` (`session.start`/`user.message`) with a `data` payload =>
Copilot CLI; top-level `type` + `sessionId`/`timestamp` => Claude Code. Claude
Code subagent transcripts (<session>/subagents/agent-*.jsonl) work too.

Raw transcripts are large (90 KB-4 MB) and full of tool-call noise. This
emits, per turn: the user query, the assistant's prose, and a one-line summary
of each tool call (name + its primary argument). Tool *outputs* are summarised
away on both sides.

Use --max-chars to cap the output. When the cap is hit, the TAIL is kept (the
final assistant summary of a session is usually the most valuable part) and a
marker notes how many earlier turns were omitted.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

TS_RE = re.compile(r"<timestamp>(.*?)</timestamp>")
UQ_RE = re.compile(r"<user_query>(.*?)</user_query>", re.S)
OFFSET_RE = re.compile(r"\(UTC([+-])(\d+):(\d+)\)")
# Harness-injected blocks inside user messages that are not the user's prompt.
INJECTED_BLOCK_RE = re.compile(
    r"<(system-reminder|task-notification|local-command-stdout|ide_opened_file|ide_selection)>"
    r"[\s\S]*?</\1>")
COMMAND_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>")
COMMAND_ARGS_RE = re.compile(r"<command-args>([\s\S]*?)</command-args>")
COMPACT_PREFIX = "This session is being continued from a previous"

# Per-tool, the input fields (in preference order) that best identify what the
# call did. Cursor and Claude Code use different key names for some tools of
# the same name (e.g. Read: `path` vs `file_path`), hence lists.
TOOL_ARG = {
    # Cursor
    "Shell": ["command"],
    "StrReplace": ["path"],
    "Delete": ["path"],
    "SemanticSearch": ["query"],
    "EditNotebook": ["target_notebook"],
    # Claude Code
    "Bash": ["command"],
    "Edit": ["file_path", "path"],
    "NotebookEdit": ["notebook_path"],
    "Agent": ["description", "prompt"],
    "Skill": ["skill"],
    # Both (different or identical keys)
    "Read": ["file_path", "path"],
    "Write": ["file_path", "path"],
    "Glob": ["pattern", "glob_pattern"],
    "Grep": ["pattern"],
    "WebSearch": ["query", "search_term"],
    "WebFetch": ["url"],
    "Task": ["description", "prompt"],
    # Codex
    "exec_command": ["cmd"],
    "shell": ["command"],
    "spawn_agent": ["agent_type", "message"],
    "wait_agent": ["targets"],
    "apply_patch": ["input", "patch"],
    # Copilot
    "run_in_terminal": ["command"],
    "read_file": ["filePath"],
    "create_file": ["filePath"],
    "replace_string_in_file": ["filePath"],
    "multi_replace_string_in_file": ["explanation"],
    "grep_search": ["query"],
    "file_search": ["query"],
    "semantic_search": ["query"],
    "list_dir": ["path"],
    "runSubagent": ["description"],
    "fetch_webpage": ["urls", "query"],
}


def clean_ts(text: str) -> str:
    m = TS_RE.search(text)
    if not m:
        return ""
    s = OFFSET_RE.sub("", m.group(1)).strip()
    return s


def fmt_claude_ts(ts) -> str:
    """Render a Claude Code ISO8601 UTC timestamp in the same local-time style
    Cursor embeds, so per-turn headers look identical across formats."""
    try:
        d = dt.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    local = d.astimezone()
    return (f"{local.strftime('%A, %b')} {local.day}, {local.year}, "
            f"{local.strftime('%I:%M %p').lstrip('0')}")


def tool_summary(block: dict) -> str:
    name = block.get("name", "tool")
    inp = block.get("input") or {}
    val = None
    if name == "TodoWrite":
        todos = inp.get("todos")
        if isinstance(todos, list):
            val = f"{len(todos)} items"
    elif name == "AskUserQuestion":
        qs = inp.get("questions")
        if isinstance(qs, list) and qs and isinstance(qs[0], dict):
            val = qs[0].get("question")
    if val is None:
        for key in TOOL_ARG.get(name, ()):
            if key in inp:
                val = inp[key]
                break
    if val is None:
        for k in ("command", "cmd", "path", "file_path", "filePath", "pattern",
                  "query", "url", "urls", "description", "prompt", "message", "agent_type"):
            if k in inp:
                val = inp[k]
                break
    if val is None:
        val = json.dumps(inp)[:80]
    val = re.sub(r"\s+", " ", str(val)).strip()
    if len(val) > 160:
        val = val[:157] + "..."
    return f"{name}({val})"


def strip_query_text(text: str) -> str:
    """Pull the human-authored query out of a Cursor user message, dropping the
    injected context blobs (plugin_info, rules, attached files, timestamps)."""
    queries = UQ_RE.findall(text)
    if queries:
        return "\n".join(re.sub(r"\s+\n", "\n", q).strip() for q in queries)
    # Fallback: drop obvious injected XML-ish blocks, keep the rest.
    cleaned = re.sub(r"<(timestamp|plugin_info|system_reminder|attached_files|"
                     r"open_and_recently_viewed_files|code_selection)[\s\S]*?</\1>",
                     "", text)
    return cleaned.strip()


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
    text = INJECTED_BLOCK_RE.sub("", text).strip()
    if text.startswith(COMPACT_PREFIX):
        text = "[compaction summary] " + re.sub(r"\s+", " ", text)[:300] + "..."
    return text


def detect_format(path: Path) -> str:
    """Return "cursor", "claude", "codex", or "copilot" by sniffing the first
    parseable lines."""
    with path.open() as f:
        for i, line in enumerate(f):
            if i >= 50:
                break
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("role") in ("user", "assistant"):
                return "cursor"
            typ = obj.get("type")
            # Codex rollout records wrap everything in a `payload` envelope.
            if typ in ("session_meta", "response_item", "event_msg", "turn_context") and "payload" in obj:
                return "codex"
            # Copilot CLI events use dotted types (session.start, user.message)
            # with a `data` payload.
            if isinstance(typ, str) and "data" in obj and typ.split(".", 1)[0] in (
                    "session", "user", "assistant", "tool", "permission", "hook", "system"):
                return "copilot"
            if typ and ("sessionId" in obj or "timestamp" in obj):
                return "claude"
    sys.exit(f"error: cannot detect transcript format: {path}")


def iter_turns_cursor(path: Path):
    """Yield turns as dicts: {ts, user, assistant_text, tools[]}."""
    turn = None
    with path.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = obj.get("role")
            if role == "user":
                if turn is not None:
                    yield turn
                content = (obj.get("message") or {}).get("content") or []
                text = "\n".join(b.get("text", "") for b in content
                                 if isinstance(b, dict) and b.get("type") == "text")
                turn = {
                    "ts": clean_ts(text),
                    "user": strip_query_text(text),
                    "assistant_text": [],
                    "tools": [],
                }
            elif role == "assistant":
                if turn is None:
                    turn = {"ts": "", "user": "(no preceding user message)",
                            "assistant_text": [], "tools": []}
                content = (obj.get("message") or {}).get("content") or []
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        turn["assistant_text"].append(b["text"].strip())
                    elif b.get("type") == "tool_use":
                        turn["tools"].append(tool_summary(b))
    if turn is not None:
        yield turn


def parse_claude(path: Path):
    """Return (turns, meta) for a Claude Code transcript. A turn starts at
    each real user prompt; tool_result-carrier and isMeta user lines are not
    turns. meta carries the session cwd and AI-generated title."""
    meta = {"cwd": None, "title": ""}
    turns = []
    turn = None
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
                meta["title"] = obj.get("aiTitle") or meta["title"]
                continue
            if meta["cwd"] is None and isinstance(obj.get("cwd"), str):
                meta["cwd"] = obj["cwd"]
            if typ == "user":
                if obj.get("isMeta"):
                    continue
                text = clean_claude_user_text((obj.get("message") or {}).get("content"))
                if not text:
                    continue
                if turn is not None:
                    turns.append(turn)
                turn = {
                    "ts": fmt_claude_ts(obj.get("timestamp")),
                    "user": text,
                    "assistant_text": [],
                    "tools": [],
                }
            elif typ == "assistant":
                if turn is None:
                    turn = {"ts": fmt_claude_ts(obj.get("timestamp")),
                            "user": "(no preceding user message)",
                            "assistant_text": [], "tools": []}
                content = (obj.get("message") or {}).get("content")
                if isinstance(content, str):
                    if content.strip():
                        turn["assistant_text"].append(content.strip())
                    continue
                for b in content or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        turn["assistant_text"].append(b["text"].strip())
                    elif b.get("type") == "tool_use":
                        turn["tools"].append(tool_summary(b))
    if turn is not None:
        turns.append(turn)
    return turns, meta


CODEX_REQUEST_MARKER = "## My request for Codex:"


def clean_codex_user_text(message) -> str:
    """Extract the human request from a Codex `event_msg/user_message`. The text
    may be wrapped in an IDE-context preamble ("# Context from my IDE setup: ...
    ## My request for Codex: <real>"); keep only the real request."""
    if not isinstance(message, str):
        return ""
    text = message
    if CODEX_REQUEST_MARKER in text:
        text = text.split(CODEX_REQUEST_MARKER, 1)[1]
    return text.strip()


def codex_tool_summary(payload: dict) -> str:
    """Normalise a Codex `function_call` payload (arguments is a JSON string)
    into the shared tool_summary shape."""
    raw = payload.get("arguments")
    inp = {}
    if isinstance(raw, str):
        try:
            inp = json.loads(raw)
        except (ValueError, TypeError):
            inp = {"args": raw}
    elif isinstance(raw, dict):
        inp = raw
    return tool_summary({"name": payload.get("name", "tool"), "input": inp})


def parse_codex(path: Path):
    """Return (turns, meta) for a Codex rollout transcript. A turn starts at each
    real user prompt (the `event_msg/user_message` event); injected AGENTS.md /
    environment / subagent_notification text appears only as `response_item`
    user messages and is ignored. meta carries the session cwd and thread title."""
    meta = {"cwd": None, "title": ""}
    turns = []
    turn = None
    with path.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            rt = obj.get("type")
            payload = obj.get("payload") or {}
            ts = obj.get("timestamp")
            if rt == "session_meta":
                if meta["cwd"] is None and isinstance(payload.get("cwd"), str):
                    meta["cwd"] = payload["cwd"]
            elif rt == "event_msg":
                pt = payload.get("type")
                if pt == "thread_name_updated":
                    meta["title"] = payload.get("thread_name") or meta["title"]
                elif pt == "user_message":
                    text = clean_codex_user_text(payload.get("message"))
                    if text:
                        if turn is not None:
                            turns.append(turn)
                        turn = {"ts": fmt_claude_ts(ts), "user": text,
                                "assistant_text": [], "tools": []}
            elif rt == "response_item":
                pt = payload.get("type")
                if pt == "message" and payload.get("role") == "assistant":
                    if turn is None:
                        turn = {"ts": fmt_claude_ts(ts),
                                "user": "(no preceding user message)",
                                "assistant_text": [], "tools": []}
                    txt = "\n".join(b.get("text", "") for b in payload.get("content", [])
                                    if isinstance(b, dict) and b.get("type") == "output_text")
                    if txt.strip():
                        turn["assistant_text"].append(txt.strip())
                elif pt == "function_call":
                    if turn is None:
                        turn = {"ts": fmt_claude_ts(ts),
                                "user": "(no preceding user message)",
                                "assistant_text": [], "tools": []}
                    turn["tools"].append(codex_tool_summary(payload))
    if turn is not None:
        turns.append(turn)
    return turns, meta


def parse_copilot(path: Path):
    """Return (turns, meta) for a Copilot CLI `events.jsonl` transcript. Turns
    start at each `user.message` (data.content is the clean prompt); assistant
    prose and tool calls come from `assistant.message` (data.content +
    data.toolRequests). meta carries the session cwd."""
    meta = {"cwd": None, "title": ""}
    turns = []
    turn = None
    with path.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            t = obj.get("type")
            data = obj.get("data") or {}
            ts = obj.get("timestamp")
            if t == "session.start":
                ctx = data.get("context") or {}
                if meta["cwd"] is None and isinstance(ctx.get("cwd"), str):
                    meta["cwd"] = ctx["cwd"]
            elif t == "user.message":
                content = data.get("content")
                if isinstance(content, str) and content.strip():
                    if turn is not None:
                        turns.append(turn)
                    turn = {"ts": fmt_claude_ts(ts), "user": content.strip(),
                            "assistant_text": [], "tools": []}
            elif t == "assistant.message":
                if turn is None:
                    turn = {"ts": fmt_claude_ts(ts),
                            "user": "(no preceding user message)",
                            "assistant_text": [], "tools": []}
                content = data.get("content")
                if isinstance(content, str) and content.strip():
                    turn["assistant_text"].append(content.strip())
                for tr in data.get("toolRequests") or []:
                    if isinstance(tr, dict):
                        turn["tools"].append(
                            tool_summary({"name": tr.get("name", "tool"),
                                          "input": tr.get("arguments") or {}}))
    if turn is not None:
        turns.append(turn)
    return turns, meta


def render_turn(idx: int, turn: dict, no_tools: bool) -> str:
    lines = []
    head = f"--- turn {idx}"
    if turn["ts"]:
        head += f" [{turn['ts']}]"
    head += " ---"
    lines.append(head)
    if turn["user"]:
        lines.append(f"USER: {turn['user']}")
    if turn["assistant_text"]:
        lines.append("ASSISTANT: " + "\n\n".join(turn["assistant_text"]))
    if turn["tools"] and not no_tools:
        lines.append("tools: " + "; ".join(turn["tools"]))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="path to a session .jsonl transcript")
    ap.add_argument("--max-chars", type=int, default=24000, help="cap output size (tail kept)")
    ap.add_argument("--no-tools", action="store_true", help="omit tool-call summaries")
    args = ap.parse_args()

    path = Path(args.path).expanduser()
    if not path.is_file():
        sys.exit(f"error: not a file: {path}")

    fmt = detect_format(path)
    title = ""
    agent_info = ""
    if fmt == "cursor":
        turns = list(iter_turns_cursor(path))
        project = path.parents[2].name
    elif fmt == "codex":
        turns, meta = parse_codex(path)
        project = Path(meta["cwd"]).name if meta["cwd"] else path.stem
        title = meta["title"]
    elif fmt == "copilot":
        turns, meta = parse_copilot(path)
        project = Path(meta["cwd"]).name if meta["cwd"] else path.parent.name
        title = meta["title"]
    else:
        turns, meta = parse_claude(path)
        project = Path(meta["cwd"]).name if meta["cwd"] else path.parent.name
        title = meta["title"]
        if path.parent.name == "subagents":
            meta_file = path.parent / (path.stem + ".meta.json")
            if meta_file.is_file():
                try:
                    m = json.loads(meta_file.read_text())
                    agent_info = " — ".join(
                        str(x) for x in (m.get("agentType"), m.get("description")) if x)
                except (OSError, ValueError):
                    pass

    first_query = next((t["user"] for t in turns if t["user"]
                        and not t["user"].startswith("(no preceding")), "")

    header = [
        f"=== SESSION {path.stem} (project: {project}) ===",
        f"turns: {len(turns)}",
    ]
    if title:
        header.append(f"title: {title}")
    if agent_info:
        header.append(f"agent: {agent_info}")
    if first_query:
        header.append(f"first query: {re.sub(chr(10), ' ', first_query)[:200]}")
    header_str = "\n".join(header)

    rendered = [render_turn(i + 1, t, args.no_tools) for i, t in enumerate(turns)]

    body = "\n\n".join(rendered)
    budget = args.max_chars - len(header_str) - 100
    if len(body) > budget and budget > 0:
        kept = []
        total = 0
        omitted = 0
        for i in range(len(rendered) - 1, -1, -1):
            chunk = rendered[i]
            if total + len(chunk) > budget and kept:
                omitted = i + 1
                break
            kept.append(chunk)
            total += len(chunk) + 2
        kept.reverse()
        marker = f"[... {omitted} earlier turn(s) omitted to fit --max-chars; tail kept ...]"
        body = marker + "\n\n" + "\n\n".join(kept)

    print(header_str)
    print()
    print(body)


if __name__ == "__main__":
    main()

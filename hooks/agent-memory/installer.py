#!/usr/bin/env python3
"""Installer for the agent-memory hooks (Claude Code, Codex, Cursor, Copilot).

Idempotent: re-running upgrades registrations in place. It also de-registers
the legacy session-scratchpad hooks (the predecessor of this system) so two
memory authorities never run side by side. Existing user configuration outside
the agent-memory/session-scratchpad entries is preserved verbatim; JSON files
are re-serialized (formatting may change, content does not).

Usage: installer.py [--home DIR] [--repo DIR] [--skip-doctor]
  --home  target home directory (default: $HOME; used by tests)
  --repo  agent-skills clone (default: derived from this file's location)
"""

import json
import os
import re
import shlex
import stat
import subprocess
import sys

HOOK_EVENTS = ("session-start", "prompt", "post-tool", "stop",
               "pre-compact", "session-end")
LEGACY_MARK = "session-scratchpad"
OURS_MARK = "agent-memory"
INSTR_HEADER = "## Agent working memory"
INSTR_END = "<!-- /agent-memory -->"
LEGACY_INSTR_HEADER = "## Session state tracking"


def log(agent, msg):
    print("[%s] %s" % (agent, msg))


def read(path):
    # surrogateescape round-trips non-UTF-8 bytes through read+write, so a
    # Latin-1 CLAUDE.md neither crashes the installer nor gets mangled
    try:
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            return f.read()
    except OSError:
        return ""


def write(path, text):
    # follow symlinks: dotfile-managed configs must not be replaced by
    # regular files at the link path
    if os.path.islink(path):
        path = os.path.realpath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(text)
    os.replace(tmp, path)


def backup_once(path):
    if os.path.exists(path) and not os.path.exists(path + ".bak"):
        write(path + ".bak", read(path))


def symlink(target, link):
    os.makedirs(os.path.dirname(link), exist_ok=True)
    try:
        if os.path.islink(link) or os.path.exists(link):
            os.remove(link)
    except OSError:
        pass
    os.symlink(target, link)


def snippet(repo, name):
    return read(os.path.join(repo, "hooks", "agent-memory", "snippets", name))


def core_script(repo):
    return os.path.join(repo, "hooks", "agent-memory", "agent_memory.py")


# --- markdown section surgery -------------------------------------------------


def strip_section(text, header, end_marker=None):
    """Remove a '## Header' section. With end_marker (our own sections are
    written with a terminating '<!-- /agent-memory -->' line) the strip is
    exactly header..marker — trailing user notes, even headingless ones, are
    safe. Without it (legacy sections), fall back to stopping at the next
    heading of ANY level, so '# Memories' blocks appended by Claude's '#'
    shortcut are never eaten."""
    lines = text.splitlines()
    out, skipping = [], False
    use_marker = bool(end_marker) and end_marker in text
    for line in lines:
        if line.strip() == header:
            skipping = True
            continue
        if skipping:
            if use_marker:
                if line.strip() == end_marker:
                    skipping = False
                continue
            if re.match(r"^#{1,6} ", line):
                skipping = False
        if not skipping:
            out.append(line)
    result = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", result)


def instructions_section(repo, hook_path):
    text = snippet(repo, "instructions.snippet.md")
    text = re.sub(r"<!--.*?-->\s*", "", text, flags=re.DOTALL)
    return (text.replace("__HOOK__", hook_path).strip()
            + "\n" + INSTR_END + "\n")


def merge_instructions(agent, path, repo, hook_path):
    backup_once(path)
    text = read(path)
    had = INSTR_HEADER in text
    text = strip_section(text, LEGACY_INSTR_HEADER)
    text = strip_section(text, INSTR_HEADER, end_marker=INSTR_END)
    text = text.rstrip("\n")
    section = instructions_section(repo, hook_path)
    text = (text + "\n\n" if text else "") + section
    write(path, text)
    log(agent, ("updated" if had else "added") + " '%s' in %s" %
        (INSTR_HEADER, path))


# --- per-agent installs ---------------------------------------------------------


def install_claude(home, repo):
    hooks_link = os.path.join(home, ".claude", "hooks", "agent-memory.py")
    symlink(core_script(repo), hooks_link)
    log("claude", "linked %s" % hooks_link)

    path = os.path.join(home, ".claude", "settings.json")
    backup_once(path)
    cfg = {}
    if read(path).strip():
        try:
            cfg = json.loads(read(path))
        except ValueError:
            log("claude", "ERROR: %s is not valid JSON — fix it and re-run" % path)
            return False
    snip = json.loads(snippet(repo, "claude.settings.snippet.json"))

    perms = cfg.setdefault("permissions", {})
    if not isinstance(perms, dict):
        log("claude", "ERROR: settings.json 'permissions' is not an object —"
            " fix it and re-run")
        return False
    allow = perms.setdefault("allow", [])
    if not isinstance(allow, list):
        log("claude", "ERROR: settings.json 'permissions.allow' is not a list"
            " — fix it and re-run")
        return False
    allow[:] = [r for r in allow
                if "session-scratchpads" not in str(r)
                and r != "Write(~/.agent-memory/**)"]
    for rule in snip["permissions"]["allow"]:
        if rule not in allow:
            allow.append(rule)

    hooks = cfg.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        log("claude", "ERROR: settings.json 'hooks' is not an object — fix it"
            " and re-run")
        return False
    for ev in list(hooks):
        groups = [g for g in hooks[ev]
                  if LEGACY_MARK not in json.dumps(g)
                  and OURS_MARK not in json.dumps(g)]
        if groups:
            hooks[ev] = groups
        else:
            del hooks[ev]
    for ev, groups in snip["hooks"].items():
        hooks.setdefault(ev, []).extend(groups)

    write(path, json.dumps(cfg, indent=2) + "\n")
    log("claude", "registered hooks in %s (backup: settings.json.bak)" % path)
    merge_instructions("claude", os.path.join(home, ".claude", "CLAUDE.md"),
                       repo, "~/.claude/hooks/agent-memory.py")
    remove_legacy_script(home, ".claude")
    return True


def _toml_lines_with_string_state(text):
    """Yield (line, in_multiline_string_at_line_start). Tracks ''' and \"\"\"
    multiline strings — and skips over single-line quoted strings and
    comments — so section headers (or quote/hash characters) inside string
    values are never mistaken for structure."""
    in_ml = None  # None or the active multiline delimiter
    for line in text.splitlines():
        yield line, in_ml is not None
        i, n = 0, len(line)
        while i < n:
            if in_ml is not None:
                j = line.find(in_ml, i)
                if j == -1:
                    break  # string continues past this line
                in_ml = None
                i = j + 3
                continue
            if line.startswith('"""', i) or line.startswith("'''", i):
                delim = line[i:i + 3]
                j = line.find(delim, i + 3)
                if j == -1:
                    in_ml = delim
                    break
                i = j + 3
                continue
            c = line[i]
            if c == "#":
                break  # comment: rest of line is inert
            if c in "\"'":
                j = i + 1
                while j < n:
                    if c == '"' and line[j] == "\\":
                        j += 2
                        continue
                    if line[j] == c:
                        break
                    j += 1
                i = j + 1
                continue
            i += 1


def _toml_groups(text):
    """Split a TOML file into (preamble_lines, [group...]) where each group is
    a list of chunks (header line + body lines), grouped so [[hooks.X.hooks]]
    chunks stay attached to their preceding [[hooks.X]] parent. Headers inside
    multiline strings are treated as body text."""
    chunks, current, preamble = [], None, []
    for line, in_str in _toml_lines_with_string_state(text):
        if not in_str and re.match(r"^\s*\[", line):
            current = [line]
            chunks.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current.append(line)
    groups, cur = [], None
    for chunk in chunks:
        header = chunk[0].strip()
        m = re.match(r"^\[\[hooks\.([A-Za-z]+)\]\]$", header)
        sub = re.match(r"^\[\[hooks\.([A-Za-z]+)\.hooks\]\]$", header)
        if m:
            cur = [chunk]
            groups.append(cur)
        elif sub and cur and re.match(r"^\[\[hooks\.%s\]\]$" % sub.group(1),
                                      cur[0][0].strip()):
            cur.append(chunk)
        else:
            cur = None
            groups.append([chunk])
    return preamble, groups


def _is_ours_comment(line):
    """Exact-marker match only: a user's own comment that merely mentions
    'agent-skills' must never be cleaned up."""
    s = line.strip()
    if not s.startswith("#"):
        return False
    return (s.startswith("# [agent-memory]")
            or "session-scratchpad hook (added by agent-skills)" in s
            or s in ("# agent-memory hooks (added by agent-skills)",
                     "# end agent-memory hooks (added by agent-skills)"))


def _group_registers(group, needle):
    """True when a [[hooks.*]] group's NON-comment lines reference needle.
    Comment lines are ignored: the legacy installer's marker comment can sit
    attached to a USER group and must not condemn it."""
    if not re.match(r"^\s*\[\[hooks\.", group[0][0]):
        return False
    for chunk in group:
        for line in chunk:
            if line.strip().startswith("#"):
                continue
            if needle in line:
                return True
    return False


def install_codex(home, repo):
    hooks_link = os.path.join(home, ".codex", "hooks", "agent-memory.py")
    symlink(core_script(repo), hooks_link)
    log("codex", "linked %s" % hooks_link)

    path = os.path.join(home, ".codex", "config.toml")
    backup_once(path)
    text = read(path)

    # Manage individual [[hooks.*]] groups, never a text span: Codex itself
    # rewrites config.toml (trust entries, `codex mcp add`, ...) and may place
    # new tables anywhere — everything that is not verifiably ours must
    # survive byte-for-byte ([hooks.state] trust tables, [mcp_servers.*], the
    # user's own hook groups, comments).
    preamble, groups = _toml_groups(text)
    kept = []
    for group in groups:
        if (_group_registers(group, LEGACY_MARK)
                or _group_registers(group, OURS_MARK)):
            continue
        lines = [ln for chunk in group for ln in chunk
                 if not _is_ours_comment(ln)]
        kept.append("\n".join(lines))
    body = [ln for ln in preamble if not _is_ours_comment(ln)]
    text = "\n".join(body + kept).rstrip("\n")

    # Append the managed groups; snippet comments are stripped and replaced
    # by tagged lines so re-runs can clean them up again.
    block_lines = [
        "# [agent-memory] hooks — managed by the agent-skills installer;"
        " re-runs replace these groups (docs/session-memory.md)",
        "# [agent-memory] TRUST GATE: after every install/upgrade, open"
        " `codex` interactively once and trust the hooks, or `codex exec`"
        " silently skips them",
    ]
    for line in snippet(repo, "codex.config.snippet.toml").splitlines():
        if not line.strip().startswith("#"):
            block_lines.append(line)
    block = re.sub(r"\n{3,}", "\n\n", "\n".join(block_lines)).strip("\n")
    text = (text + "\n\n" if text.strip() else "") + block + "\n"
    write(path, text)
    log("codex", "registered hooks in %s (backup: config.toml.bak)" % path)
    log("codex", "TRUST GATE: run `codex` interactively once and trust the"
        " hooks — until then Codex silently skips them in headless runs")

    hooks_json = os.path.join(home, ".codex", "hooks.json")
    if os.path.exists(hooks_json) and OURS_MARK in read(hooks_json):
        log("codex", "WARNING: ~/.codex/hooks.json also references"
            " agent-memory — codex honors BOTH files; remove one or hooks run"
            " twice")

    # Codex reads AGENTS.override.md INSTEAD of AGENTS.md when it exists —
    # the ingest must land in the file Codex actually loads.
    agents_md = os.path.join(home, ".codex", "AGENTS.md")
    override = os.path.join(home, ".codex", "AGENTS.override.md")
    if os.path.exists(override):
        agents_md = override
        log("codex", "AGENTS.override.md exists — writing ingest there"
            " (AGENTS.md is ignored while it exists)")
    merge_instructions("codex", agents_md, repo,
                       "~/.codex/hooks/agent-memory.py")
    remove_legacy_script(home, ".codex")
    return True


def install_cursor(home, repo):
    hooks_link = os.path.join(home, ".cursor", "hooks", "agent-memory.py")
    symlink(core_script(repo), hooks_link)

    wrap_dir = os.path.join(home, ".cursor", "hooks", "agent-memory")
    for ev in HOOK_EVENTS:
        wrapper = os.path.join(wrap_dir, ev + ".sh")
        write(wrapper,
              "#!/usr/bin/env bash\n"
              "# generated by agent-skills installer — do not edit\n"
              'exec python3 "$HOME/.cursor/hooks/agent-memory.py"'
              " hook cursor %s\n" % ev)
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IXUSR
                 | stat.S_IXGRP | stat.S_IXOTH)
    log("cursor", "linked adapter + wrote wrappers in %s" % wrap_dir)

    path = os.path.join(home, ".cursor", "hooks.json")
    backup_once(path)
    cfg = {}
    if read(path).strip():
        try:
            cfg = json.loads(read(path))
        except ValueError:
            log("cursor", "ERROR: %s is not valid JSON — fix it and re-run" % path)
            return False
    cfg.setdefault("version", 1)
    hooks = cfg.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        log("cursor", "ERROR: hooks.json 'hooks' is not an object — fix it"
            " and re-run")
        return False
    for ev in list(hooks):
        entries = [e for e in hooks[ev]
                   if LEGACY_MARK not in json.dumps(e)
                   and OURS_MARK not in json.dumps(e)]
        if entries:
            hooks[ev] = entries
        else:
            del hooks[ev]
    # cursor-agent shell-processes the command string (verified), so the
    # wrapper path must be quoted when it needs it (e.g. HOME with spaces);
    # for such paths IDE behavior is unverified — warn.
    quoted = shlex.quote(wrap_dir)
    if quoted != wrap_dir:
        log("cursor", "WARNING: wrapper path %r needs shell quoting — quoted"
            " for the CLI; Cursor IDE behavior with such paths is unverified"
            % wrap_dir)
    snip = json.loads(snippet(repo, "cursor.hooks.snippet.json"))
    for ev, entries in snip["hooks"].items():
        for e in entries:
            e["command"] = e["command"].replace("__CURSOR_WRAPPERS__", quoted)
        hooks.setdefault(ev, []).extend(entries)
    write(path, json.dumps(cfg, indent=2) + "\n")
    log("cursor", "registered hooks in %s (backup: hooks.json.bak)" % path)
    log("cursor", "note: no global instruction file exists for Cursor —"
        " post-compaction recovery relies on the postToolUse re-injection")
    remove_legacy_script(home, ".cursor")
    return True


def install_copilot(home, repo):
    hooks_link = os.path.join(home, ".copilot", "hooks", "agent-memory.py")
    symlink(core_script(repo), hooks_link)

    path = os.path.join(home, ".copilot", "hooks", "agent-memory.json")
    new = snippet(repo, "copilot.hooks.snippet.json")
    changed = read(path) != new
    write(path, new)
    log("copilot", "linked adapter + wrote %s" % path)
    if changed:
        # The adapter script updates in place (per-event execution), but the
        # event wiring is read once at CLI startup.
        log("copilot", "hook wiring changed — restart any running copilot"
                       " sessions to pick it up")

    for legacy in ("session-scratchpad.json",):
        p = os.path.join(home, ".copilot", "hooks", legacy)
        if os.path.exists(p):
            os.remove(p)
            log("copilot", "removed legacy %s" % p)

    merge_instructions("copilot",
                       os.path.join(home, ".copilot", "copilot-instructions.md"),
                       repo, "~/.copilot/hooks/agent-memory.py")
    remove_legacy_script(home, ".copilot")
    return True


def remove_legacy_script(home, dotdir):
    p = os.path.join(home, dotdir, "hooks", "session-scratchpad.sh")
    if os.path.islink(p) or os.path.exists(p):
        try:
            os.remove(p)
            log(dotdir.lstrip("."), "removed legacy %s" % p)
        except OSError:
            pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    home = os.path.expanduser("~")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.realpath(__file__))))
    skip_doctor = False
    while argv:
        arg = argv.pop(0)
        if arg == "--home":
            home = argv.pop(0)
        elif arg == "--repo":
            repo = argv.pop(0)
        elif arg == "--skip-doctor":
            skip_doctor = True
        else:
            print(__doc__)
            return 2
    if not os.path.isfile(core_script(repo)):
        print("error: %s not found — run from an agent-skills clone" %
              core_script(repo))
        return 1
    ok = True
    for fn in (install_claude, install_codex, install_cursor, install_copilot):
        # one agent's broken/unreadable config must not abort the others
        try:
            ok = fn(home, repo) and ok
        except Exception as exc:
            log(fn.__name__.replace("install_", ""),
                "ERROR: install failed: %r — other agents continue" % exc)
            ok = False
    if not skip_doctor:
        print("\n--- doctor ---")
        env = dict(os.environ, HOME=home)
        subprocess.call([sys.executable, core_script(repo), "doctor"], env=env)
    print("\n[done] agent-memory hooks installed%s" %
          ("" if ok else " (with errors — see above)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

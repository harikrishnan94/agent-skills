#!/usr/bin/env python3
"""Tests for the agent-memory hooks (core + installer).

Runs the real CLI via subprocess with AGENT_MEMORY_HOME pointed at a temp
store, using fixture payloads whose field names match the verified on-wire
contracts of each agent (2026-07). Run: python3 -m unittest discover tests
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "hooks", "agent-memory", "agent_memory.py")
INSTALLER = os.path.join(REPO, "hooks", "agent-memory", "installer.py")

sys.path.insert(0, os.path.join(REPO, "hooks", "agent-memory"))
import agent_memory  # noqa: E402


def run(args, payload=None, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, SCRIPT] + args,
                       input=json.dumps(payload) if payload is not None else "",
                       capture_output=True, text=True, env=e, cwd=cwd,
                       timeout=60)
    return p


def out_json(p):
    return json.loads(p.stdout) if p.stdout.strip() else None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agent-memory-test-")
        self.store = os.path.join(self.tmp, "store")
        self.proj = os.path.join(self.tmp, "proj")
        os.makedirs(self.proj)
        self.env = {"AGENT_MEMORY_HOME": self.store}
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def hook(self, agent, event, payload, env=None):
        e = dict(self.env)
        e.update(env or {})
        p = run(["hook", agent, event], payload, env=e, cwd=self.proj)
        self.assertEqual(p.returncode, 0,
                         "hook must never fail: %s" % p.stderr)
        return out_json(p)

    def claude_payload(self, event_extra=None, sid="cl-sess-1"):
        p = {"session_id": sid, "cwd": self.proj,
             "transcript_path": "/tmp/t.jsonl",
             "hook_event_name": "X", "permission_mode": "default"}
        p.update(event_extra or {})
        return p

    def session_dir(self, key):
        projects = os.path.join(self.store, "projects")
        for d in os.listdir(projects):
            sdir = os.path.join(projects, d, "sessions", key)
            if os.path.isdir(sdir):
                return sdir
        raise AssertionError("session %s not found" % key)

    def write_state(self, key, objective="Fix the frobnicator",
                    now="editing frob.c", status="in-progress"):
        sdir = self.session_dir(key)
        text = agent_memory.STATE_TEMPLATE
        text = text.replace("Status: in-progress", "Status: " + status)
        text = text.replace("## Objective\n", "## Objective\n%s\n" % objective)
        text = text.replace("## Now (exact stopping point)\n",
                            "## Now (exact stopping point)\n%s\n" % now)
        with open(os.path.join(sdir, "state.md"), "w") as f:
            f.write(text)
        return sdir


class TestIdentity(Base):
    def test_non_git_path_identity_and_symlink(self):
        i1 = self._ident(self.proj)
        link = os.path.join(self.tmp, "link")
        os.symlink(self.proj, link)
        i2 = self._ident(link)
        self.assertEqual(i1["hash"], i2["hash"])
        self.assertEqual(i1["kind"], "path")

    def _ident(self, cwd):
        env = dict(os.environ, AGENT_MEMORY_HOME=self.store)
        code = ("import sys; sys.path.insert(0, %r); import agent_memory as m;"
                "import json; print(json.dumps(m.project_identity(%r)))"
                % (os.path.dirname(SCRIPT), cwd))
        p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env)
        return json.loads(p.stdout)

    def test_git_identity_stable_across_clone_and_worktree(self):
        g1 = os.path.join(self.tmp, "repo1")
        subprocess.run(["git", "init", "-q", g1], check=True)
        subprocess.run(["git", "-C", g1, "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "root"], check=True)
        g2 = os.path.join(self.tmp, "repo2")
        subprocess.run(["git", "clone", "-q", g1, g2], check=True)
        wt = os.path.join(self.tmp, "wt1")
        subprocess.run(["git", "-C", g1, "worktree", "add", "-q",
                        "-b", "side", wt], check=True)
        i1, i2, iw = self._ident(g1), self._ident(g2), self._ident(wt)
        self.assertEqual(i1["kind"], "git-root-commit")
        self.assertEqual(i1["hash"], i2["hash"])
        self.assertEqual(i1["hash"], iw["hash"])
        self.assertNotEqual(i1["worktree"], iw["worktree"])

    def test_sibling_paths_do_not_collide(self):
        a = os.path.join(self.tmp, "b-c")
        b = os.path.join(self.tmp, "b", "c")
        os.makedirs(a)
        os.makedirs(b)
        self.assertNotEqual(self._ident(a)["hash"], self._ident(b)["hash"])

    def test_remote_normalization(self):
        n = agent_memory.normalize_remote
        self.assertEqual(n("git@github.com:Me/Repo.git"), "github.com/me/repo")
        self.assertEqual(n("https://github.com/me/repo"), "github.com/me/repo")
        self.assertEqual(n("ssh://git@github.com/me/repo.git"),
                         "github.com/me/repo")


class TestSessionStart(Base):
    def test_claude_new_session_output_shape(self):
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "startup"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"],
                         "SessionStart")
        self.assertIn("AGENT WORKING MEMORY", ctx)
        self.assertIn("claude-cl-sess-1", ctx)
        self.assertIn("state.md", ctx)
        sdir = self.session_dir("claude-cl-sess-1")
        self.assertTrue(os.path.isfile(os.path.join(sdir, "state.md")))
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        self.assertEqual(meta["agent"], "claude")

    def test_cursor_payload_and_output_shape(self):
        out = self.hook("cursor", "session-start",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "hook_event_name": "sessionStart"})
        self.assertIn("additional_context", out)
        self.assertIn("cursor-cur-1", out["additional_context"])

    def test_copilot_payload_and_output_shape(self):
        out = self.hook("copilot", "session-start",
                        {"sessionId": "cop-1", "cwd": self.proj,
                         "timestamp": 1782460792611, "source": "startup"})
        self.assertIn("additionalContext", out)

    def test_codex_output_shape(self):
        out = self.hook("codex", "session-start",
                        {"session_id": "cx-1", "cwd": self.proj,
                         "source": "startup", "model": "gpt-5.5"})
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"],
                         "SessionStart")

    def test_resume_restores_state(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "resume"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Fix the frobnicator", ctx)
        self.assertIn("restored after resume", ctx)

    def test_compact_restores_state(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "compact"}))
        self.assertIn("Fix the frobnicator",
                      out["hookSpecificOutput"]["additionalContext"])

    def test_oversized_state_is_truncated(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        sdir = self.write_state("claude-cl-sess-1")
        with open(os.path.join(sdir, "state.md"), "a") as f:
            f.write("x" * 50000)
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "resume"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertLess(len(ctx.encode()), 10000)
        self.assertIn("truncated", ctx)


class TestCrossSession(Base):
    def make_finished_session(self, agent="codex", sid="cx-old"):
        payload = {"session_id": sid, "cwd": self.proj, "source": "startup"}
        self.hook(agent, "session-start", payload)
        key = "%s-%s" % (agent, sid)
        self.write_state(key)
        self.hook(agent, "session-end" if agent != "codex" else "stop",
                  payload)
        # age it past the active window
        sdir = self.session_dir(key)
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        meta["last_event_ts"] = "2026-01-01T00:00:00.000Z"
        with open(os.path.join(sdir, "meta.json"), "w") as f:
            json.dump(meta, f)
        return key

    def test_new_session_offers_candidates_and_adopt(self):
        old = self.make_finished_session()
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "startup"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Unfinished work found", ctx)
        self.assertIn(old, ctx)
        self.assertIn("Fix the frobnicator", ctx)
        self.assertIn("adopt %s --into claude-cl-sess-1" % old, ctx)

        p = run(["adopt", old, "--into", "claude-cl-sess-1"],
                env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        sdir = self.session_dir("claude-cl-sess-1")
        state = open(os.path.join(sdir, "state.md")).read()
        self.assertIn("Fix the frobnicator", state)
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        self.assertEqual(meta["resumed_from"], old)
        # lineage is derived, never written into the source session
        old_journal = open(os.path.join(self.session_dir(old),
                                        "journal.jsonl")).read()
        self.assertNotIn("adopted-by", old_journal)
        p = run(["show", old], env=self.env, cwd=self.proj)
        self.assertIn("adopted_by", p.stdout)
        self.assertIn("claude-cl-sess-1", p.stdout)

    def test_adopted_source_no_longer_offered(self):
        old = self.make_finished_session()
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        p = run(["adopt", old, "--into", "claude-cl-sess-1"],
                env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = self.hook("cursor", "session-start",
                        {"conversation_id": "cur-new",
                         "workspace_roots": [self.proj]})
        ctx = out["additional_context"]
        self.assertNotIn(old, ctx)          # superseded source hidden
        self.assertIn("claude-cl-sess-1", ctx)  # lineage tip offered

    def test_adopt_refuses_overwrite_without_force(self):
        old = self.make_finished_session()
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1", objective="Different work")
        p = run(["adopt", old, "--into", "claude-cl-sess-1"],
                env=self.env, cwd=self.proj)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--force", p.stdout)

    def test_done_sessions_not_offered(self):
        self.hook("codex", "session-start",
                  {"session_id": "cx-done", "cwd": self.proj})
        self.write_state("codex-cx-done", status="done")
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "startup"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No unfinished work", ctx)

    def test_active_session_warns_concurrent(self):
        self.hook("codex", "session-start",
                  {"session_id": "cx-live", "cwd": self.proj})
        self.write_state("codex-cx-live")
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "startup"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("CAUTION", ctx)
        self.assertIn("codex-cx-live", ctx)


class TestStaleness(Base):
    def start_and_work(self, n_tools=3):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(n_tools):
            self.hook("claude", "post-tool", self.claude_payload(
                {"tool_name": "Edit",
                 "tool_input": {"file_path": "/x/f%d.c" % i}}))
        return sdir

    def test_stale_stop_blocks_once(self):
        self.start_and_work()
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertEqual(out["decision"], "block")
        self.assertIn("stale", out["reason"])
        # second stop shortly after must not block again (rate limit)
        out2 = self.hook("claude", "stop",
                         self.claude_payload({"stop_hook_active": False}))
        self.assertIsNone(out2)

    def test_stop_hook_active_never_blocks(self):
        self.start_and_work()
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": True}))
        self.assertIsNone(out)

    def test_fresh_checkpoint_does_not_block(self):
        self.start_and_work(n_tools=2)
        self.write_state("claude-cl-sess-1", now="just checkpointed")
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIsNone(out)

    def test_soft_mode_never_blocks(self):
        self.start_and_work()
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}),
                        env={"AGENT_MEMORY_ENFORCE": "soft"})
        self.assertIsNone(out)

    def test_prompts_alone_never_stale(self):
        # A tool-free Q&A session must not be blocked at stop.
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        for q in ("what's 2+2?", "and 3+3?"):
            self.hook("claude", "prompt", self.claude_payload({"prompt": q}))
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIsNone(out)

    def test_checkpoint_write_itself_not_counted(self):
        # The Edit that updates state.md must not re-arm staleness.
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        self.hook("claude", "post-tool", self.claude_payload(
            {"tool_name": "Edit",
             "tool_input": {"file_path": os.path.join(sdir, "state.md")}}))
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIsNone(out)

    def test_user_abort_never_forces_continuation(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        sdir = self.session_dir("cursor-cur-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(3):
            self.hook("cursor", "post-tool",
                      {"conversation_id": "cur-1",
                       "workspace_roots": [self.proj], "tool_name": "Shell",
                       "tool_input": {"command": "make %d" % i}})
        out = self.hook("cursor", "stop",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "status": "aborted"})
        self.assertIsNone(out)

    def test_cursor_stop_uses_followup_message(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        sdir = self.session_dir("cursor-cur-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(3):
            self.hook("cursor", "post-tool",
                      {"conversation_id": "cur-1",
                       "workspace_roots": [self.proj], "tool_name": "Shell",
                       "tool_input": {"command": "make %d" % i}})
        out = self.hook("cursor", "stop",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "status": "completed"})
        self.assertIn("followup_message", out)


class TestReinjection(Base):
    def test_cursor_compaction_reinjects_on_next_tool(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        self.assertIsNone(
            self.hook("cursor", "pre-compact",
                      {"conversation_id": "cur-1",
                       "workspace_roots": [self.proj], "trigger": "auto"}))
        out = self.hook("cursor", "post-tool",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "tool_name": "Read",
                         "tool_input": {"file_path": "/x"}})
        self.assertIn("additional_context", out)
        self.assertIn("context recovery", out["additional_context"])
        self.assertIn("Fix the frobnicator", out["additional_context"])
        # only once
        out2 = self.hook("cursor", "post-tool",
                         {"conversation_id": "cur-1",
                          "workspace_roots": [self.proj],
                          "tool_name": "Read",
                          "tool_input": {"file_path": "/y"}})
        self.assertIsNone(out2)

    def test_pending_survives_non_injectable_prompt_event(self):
        # THE critical interactive flow: compaction (or resume) is followed by
        # the user's next prompt BEFORE any tool call. Cursor's
        # beforeSubmitPrompt cannot inject — it must not consume the armed
        # re-injection; the next post-tool must still restore state.
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        self.hook("cursor", "pre-compact",
                  {"conversation_id": "cur-1",
                   "workspace_roots": [self.proj], "trigger": "auto"})
        out = self.hook("cursor", "prompt",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "prompt": "keep going"})
        self.assertIsNone(out)  # cannot inject here...
        out = self.hook("cursor", "post-tool",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "tool_name": "Read",
                         "tool_input": {"file_path": "/x"}})
        self.assertIn("additional_context", out)  # ...but not lost
        self.assertIn("Fix the frobnicator", out["additional_context"])

    def test_copilot_pending_survives_prompt_event(self):
        self.hook("copilot", "session-start",
                  {"sessionId": "cop-1", "cwd": self.proj})
        self.write_state("copilot-cop-1")
        self.hook("copilot", "pre-compact",
                  {"sessionId": "cop-1", "cwd": self.proj,
                   "trigger": "manual"})
        self.assertIsNone(self.hook("copilot", "prompt",
                                    {"sessionId": "cop-1", "cwd": self.proj,
                                     "prompt": "continue"}))
        out = self.hook("copilot", "post-tool",
                        {"sessionId": "cop-1", "cwd": self.proj,
                         "toolName": "view", "toolArgs": "{}"})
        self.assertIn("additionalContext", out)

    def test_codex_compaction_reinjects_on_next_prompt(self):
        self.hook("codex", "session-start",
                  {"session_id": "cx-1", "cwd": self.proj})
        self.write_state("codex-cx-1")
        self.hook("codex", "pre-compact",
                  {"session_id": "cx-1", "cwd": self.proj,
                   "trigger": "manual"})
        self.hook("codex", "post-compact",
                  {"session_id": "cx-1", "cwd": self.proj,
                   "trigger": "manual"})
        out = self.hook("codex", "prompt",
                        {"session_id": "cx-1", "cwd": self.proj,
                         "prompt": "continue"})
        self.assertIn("context recovery",
                      out["hookSpecificOutput"]["additionalContext"])

    def test_claude_compaction_does_not_arm_reinjection(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        self.hook("claude", "pre-compact",
                  self.claude_payload({"trigger": "auto"}))
        out = self.hook("claude", "prompt",
                        self.claude_payload({"prompt": "hi"}))
        self.assertIsNone(out)  # SessionStart(compact) handles claude

    def test_gap_reinjection_for_cursor_resume(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        sdir = self.session_dir("cursor-cur-1")
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        meta["last_event_ts"] = "2026-01-01T00:00:00.000Z"
        with open(os.path.join(sdir, "meta.json"), "w") as f:
            json.dump(meta, f)
        out = self.hook("cursor", "post-tool",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj],
                         "tool_name": "Shell",
                         "tool_input": {"command": "ls"}})
        self.assertIn("additional_context", out)
        self.assertIn("gap", out["additional_context"])


class TestLifecycleAndRobustness(Base):
    def test_session_end_records_reason(self):
        self.hook("copilot", "session-start",
                  {"sessionId": "cop-1", "cwd": self.proj})
        self.hook("copilot", "session-end",
                  {"sessionId": "cop-1", "cwd": self.proj,
                   "reason": "complete"})
        meta = json.load(open(os.path.join(
            self.session_dir("copilot-cop-1"), "meta.json")))
        self.assertEqual(meta["status"], "ended")
        self.assertEqual(meta["end_reason"], "complete")

    def test_interrupted_session_is_visible(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        meta["last_event_ts"] = "2026-01-01T00:00:00.000Z"
        with open(os.path.join(sdir, "meta.json"), "w") as f:
            json.dump(meta, f)
        p = run(["status"], env=self.env, cwd=self.proj)
        self.assertIn("interrupted", p.stdout)

    def test_malformed_stdin_is_harmless(self):
        e = dict(os.environ, AGENT_MEMORY_HOME=self.store)
        p = subprocess.run([sys.executable, SCRIPT, "hook", "claude",
                            "session-start"], input="not json {{{",
                           capture_output=True, text=True, env=e,
                           cwd=self.proj, timeout=60)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")

    def test_unknown_agent_or_event_is_harmless(self):
        for args in (["hook", "vim", "session-start"],
                     ["hook", "claude", "banana"]):
            p = run(args, {}, env=self.env, cwd=self.proj)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout, "")

    def test_disable_env(self):
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "startup"}),
                        env={"AGENT_MEMORY_DISABLE": "1"})
        self.assertIsNone(out)

    def test_copilot_toolargs_as_json_string(self):
        self.hook("copilot", "session-start",
                  {"sessionId": "cop-1", "cwd": self.proj})
        self.hook("copilot", "post-tool",
                  {"sessionId": "cop-1", "cwd": self.proj,
                   "toolName": "bash",
                   "toolArgs": "{\"command\": \"make all\"}",
                   "toolResult": {"resultType": "success"}})
        journal = open(os.path.join(self.session_dir("copilot-cop-1"),
                                    "journal.jsonl")).read()
        self.assertIn("make all", journal)

    def test_fresh_archives_state(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        p = run(["fresh", "--session", "claude-cl-sess-1"],
                env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 0)
        sdir = self.session_dir("claude-cl-sess-1")
        state = open(os.path.join(sdir, "state.md")).read()
        self.assertNotIn("frobnicator", state)
        archived = os.listdir(os.path.join(sdir, "archive"))
        self.assertEqual(len(archived), 1)


class TestQueries(Base):
    def seed(self):
        self.hook("codex", "session-start",
                  {"session_id": "cx-1", "cwd": self.proj})
        self.write_state("codex-cx-1", objective="Migrate frobnicator to v2")
        self.hook("codex", "prompt",
                  {"session_id": "cx-1", "cwd": self.proj,
                   "prompt": "please migrate the frobnicator"})

    def test_search_finds_state_and_journal_with_provenance(self):
        self.seed()
        p = run(["search", "frobnicator"], env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 0)
        self.assertIn("codex-cx-1", p.stdout)
        self.assertIn("state.md", p.stdout)
        self.assertIn("journal.jsonl", p.stdout)

    def test_bad_cli_arguments_do_not_traceback(self):
        for args in (["search", "foo", "--limit"],
                     ["search", "foo", "--limit", "abc"],
                     ["prune", "--days", "xyz"],
                     ["fresh", "--session"]):
            p = run(args, env=self.env, cwd=self.proj)
            self.assertEqual(p.returncode, 2, args)
            self.assertNotIn("Traceback", p.stderr)

    def test_shell_checkpoint_write_not_counted(self):
        # a heredoc checkpoint whose state path sits deep in the command
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        cmd = "cd /some/very/long/path && " + "true && " * 40 + \
              "cat > %s <<EOF\nstate\nEOF" % os.path.join(sdir, "state.md")
        self.hook("claude", "post-tool", self.claude_payload(
            {"tool_name": "Bash", "tool_input": {"command": cmd}}))
        journal = open(os.path.join(sdir, "journal.jsonl")).read()
        self.assertNotIn('"ev": "tool"', journal)

    def test_search_no_match_exit_code(self):
        self.seed()
        p = run(["search", "zebra-unicorn"], env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 1)

    def test_status_lists_objective(self):
        self.seed()
        p = run(["status"], env=self.env, cwd=self.proj)
        self.assertIn("Migrate frobnicator", p.stdout)
        pj = run(["status", "--json"], env=self.env, cwd=self.proj)
        rows = json.loads(pj.stdout)
        self.assertEqual(rows[0]["agent"], "codex")

    def test_show_dumps_session(self):
        self.seed()
        p = run(["show", "codex-cx-1"], env=self.env, cwd=self.proj)
        self.assertIn("Migrate frobnicator", p.stdout)
        self.assertIn("journal", p.stdout)

    def test_prune_archives_and_search_still_finds(self):
        self.seed()
        self.hook("codex", "session-end",
                  {"session_id": "cx-1", "cwd": self.proj})
        sdir = self.session_dir("codex-cx-1")
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        meta["last_event_ts"] = "2026-01-01T00:00:00.000Z"
        meta["status"] = "ended"
        with open(os.path.join(sdir, "meta.json"), "w") as f:
            json.dump(meta, f)
        p = run(["prune", "--days", "30"], env=self.env, cwd=self.proj)
        self.assertIn("archived 1", p.stdout)
        p = run(["search", "frobnicator"], env=self.env, cwd=self.proj)
        self.assertEqual(p.returncode, 0)


class TestInstaller(Base):
    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def seed_legacy(self):
        # legacy claude settings with scratchpad hooks + old PreCompact echo
        os.makedirs(os.path.join(self.home, ".claude"))
        with open(os.path.join(self.home, ".claude", "settings.json"), "w") as f:
            json.dump({
                "model": "opus",
                "permissions": {"allow": [
                    "Read(~/.claude-session-scratchpads/**)",
                    "Bash(ls:*)"]},
                "hooks": {
                    "SessionStart": [{"matcher": "startup|resume|compact",
                                      "hooks": [{"type": "command",
                                                 "command": "bash ~/.claude/hooks/session-scratchpad.sh"}]}],
                    "PreCompact": [{"hooks": [{"type": "command",
                                               "command": "echo scratchpad path under ~/.claude-session-scratchpads"}]}]},
            }, f)
        with open(os.path.join(self.home, ".claude", "CLAUDE.md"), "w") as f:
            f.write("# my rules\n\n## Session state tracking\nold text\n"
                    "- old bullet\n\n## Other section\nkeep me\n")
        # legacy codex config
        os.makedirs(os.path.join(self.home, ".codex"))
        with open(os.path.join(self.home, ".codex", "config.toml"), "w") as f:
            f.write('model = "gpt-5.5"\n\n'
                    "# session-scratchpad hook (added by agent-skills)\n"
                    "[[hooks.SessionStart]]\n"
                    'matcher = "startup|resume|compact"\n\n'
                    "[[hooks.SessionStart.hooks]]\n"
                    'type = "command"\n'
                    'command = "bash $HOME/.codex/hooks/session-scratchpad.sh"\n'
                    'statusMessage = "Loading session scratchpad"\n')
        # legacy cursor hooks.json
        os.makedirs(os.path.join(self.home, ".cursor"))
        with open(os.path.join(self.home, ".cursor", "hooks.json"), "w") as f:
            json.dump({"version": 1, "hooks": {"sessionStart": [
                {"command": "/x/.cursor/hooks/session-scratchpad.sh"}]}}, f)
        # legacy copilot hook file
        os.makedirs(os.path.join(self.home, ".copilot", "hooks"))
        with open(os.path.join(self.home, ".copilot", "hooks",
                               "session-scratchpad.json"), "w") as f:
            json.dump({"version": 1}, f)

    def install(self):
        p = subprocess.run([sys.executable, INSTALLER, "--home", self.home,
                            "--repo", REPO, "--skip-doctor"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def test_install_from_scratch_then_doctor_passes(self):
        self.install()
        env = dict(os.environ, HOME=self.home,
                   AGENT_MEMORY_HOME=os.path.join(self.home, ".agent-memory"))
        p = subprocess.run([sys.executable, SCRIPT, "doctor"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn("[FAIL]", p.stdout)

    def test_legacy_configs_are_replaced(self):
        self.seed_legacy()
        self.install()
        cfg = json.load(open(os.path.join(self.home, ".claude",
                                          "settings.json")))
        s = json.dumps(cfg)
        self.assertNotIn("session-scratchpad", s)
        self.assertEqual(cfg["model"], "opus")  # unrelated config preserved
        self.assertIn("Bash(ls:*)", s)
        for ev in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop",
                   "PreCompact", "SessionEnd"):
            self.assertIn("agent-memory", json.dumps(cfg["hooks"][ev]))
        toml = open(os.path.join(self.home, ".codex", "config.toml")).read()
        self.assertNotIn("session-scratchpad", toml)
        self.assertIn('model = "gpt-5.5"', toml)
        self.assertIn("agent-memory", toml)
        cur = json.load(open(os.path.join(self.home, ".cursor", "hooks.json")))
        self.assertNotIn("session-scratchpad", json.dumps(cur))
        self.assertFalse(os.path.exists(os.path.join(
            self.home, ".copilot", "hooks", "session-scratchpad.json")))
        md = open(os.path.join(self.home, ".claude", "CLAUDE.md")).read()
        self.assertNotIn("## Session state tracking", md)
        self.assertIn("## Agent working memory", md)
        self.assertIn("keep me", md)

    def test_idempotent(self):
        self.install()
        self.install()
        cfg = json.load(open(os.path.join(self.home, ".claude",
                                          "settings.json")))
        self.assertEqual(len(cfg["hooks"]["SessionStart"]), 1)
        toml = open(os.path.join(self.home, ".codex", "config.toml")).read()
        self.assertEqual(toml.count("hook codex session-start"), 1)
        self.assertEqual(toml.count("TRUST GATE"), 1)
        cur = json.load(open(os.path.join(self.home, ".cursor", "hooks.json")))
        self.assertEqual(len(cur["hooks"]["sessionStart"]), 1)
        md = open(os.path.join(self.home, ".claude", "CLAUDE.md")).read()
        self.assertEqual(md.count("## Agent working memory"), 1)

    def test_cursor_wrappers_executable(self):
        self.install()
        wrap = os.path.join(self.home, ".cursor", "hooks", "agent-memory")
        for ev in ("session-start", "prompt", "post-tool", "stop",
                   "pre-compact", "session-end"):
            w = os.path.join(wrap, ev + ".sh")
            self.assertTrue(os.path.isfile(w))
            self.assertTrue(os.stat(w).st_mode & stat.S_IXUSR)

    def test_doctor_detects_drift(self):
        self.install()
        os.remove(os.path.join(self.home, ".cursor", "hooks", "agent-memory",
                               "stop.sh"))
        env = dict(os.environ, HOME=self.home,
                   AGENT_MEMORY_HOME=os.path.join(self.home, ".agent-memory"))
        p = subprocess.run([sys.executable, SCRIPT, "doctor"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("[FAIL]", p.stdout)

    def test_doctor_detects_adapter_version_drift(self):
        self.install()
        # replace the symlinked adapter with a stale copy
        link = os.path.join(self.home, ".claude", "hooks", "agent-memory.py")
        os.remove(link)
        with open(SCRIPT) as f:
            stale = f.read() + "\n# stale\n"
        with open(link, "w") as f:
            f.write(stale)
        env = dict(os.environ, HOME=self.home,
                   AGENT_MEMORY_HOME=os.path.join(self.home, ".agent-memory"))
        p = subprocess.run([sys.executable, SCRIPT, "doctor"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("drift", p.stdout)

    def test_codex_reinstall_preserves_appended_config(self):
        # Codex appends [hooks.state] trust tables and [mcp_servers.*] AFTER
        # our groups; a re-install must not eat them (reproduced data loss in
        # review with the marker-span approach).
        self.install()
        cfg = os.path.join(self.home, ".codex", "config.toml")
        with open(cfg, "a") as f:
            f.write('\n[mcp_servers.t1]\ncommand = "echo"\n'
                    '\n[hooks.state."~/.codex/config.toml:session_start:0:0"]\n'
                    'trusted_hash = "sha256:abc"\n')
        self.install()
        toml = open(cfg).read()
        self.assertIn("[mcp_servers.t1]", toml)
        self.assertIn("trusted_hash", toml)
        self.assertEqual(toml.count('hook codex session-start'), 1)

    def test_codex_user_hook_group_survives_legacy_comment(self):
        # The legacy marker comment attaches to the preceding chunk; a user's
        # own [[hooks.*]] group before it must survive the legacy cleanup.
        os.makedirs(os.path.join(self.home, ".codex"))
        with open(os.path.join(self.home, ".codex", "config.toml"), "w") as f:
            f.write('[[hooks.SessionStart]]\n\n'
                    '[[hooks.SessionStart.hooks]]\n'
                    'type = "command"\n'
                    'command = "bash /Users/hari/bin/my-own-banner.sh"\n\n'
                    "# session-scratchpad hook (added by agent-skills)\n"
                    "[[hooks.SessionStart]]\n"
                    'matcher = "startup|resume|compact"\n\n'
                    "[[hooks.SessionStart.hooks]]\n"
                    'type = "command"\n'
                    'command = "bash $HOME/.codex/hooks/session-scratchpad.sh"\n')
        self.install()
        toml = open(os.path.join(self.home, ".codex", "config.toml")).read()
        self.assertIn("my-own-banner.sh", toml)
        self.assertNotIn("session-scratchpad.sh", toml)

    def test_instructions_preserve_trailing_user_content(self):
        # Claude's '#' memory shortcut appends H1 blocks at EOF — a re-run
        # must not eat content that follows the managed section.
        self.install()
        md_path = os.path.join(self.home, ".claude", "CLAUDE.md")
        with open(md_path, "a") as f:
            f.write("\n# Memories\n- deploy uses blue/green\n")
        self.install()
        md = open(md_path).read()
        self.assertIn("deploy uses blue/green", md)
        self.assertEqual(md.count("## Agent working memory"), 1)

    def test_non_utf8_instruction_file_does_not_abort(self):
        os.makedirs(os.path.join(self.home, ".claude"), exist_ok=True)
        with open(os.path.join(self.home, ".claude", "CLAUDE.md"), "wb") as f:
            f.write(b"# caf\xe9 notes\n")  # latin-1 byte
        self.install()  # must succeed and install all four agents
        self.assertTrue(os.path.exists(os.path.join(
            self.home, ".copilot", "hooks", "agent-memory.json")))
        raw = open(os.path.join(self.home, ".claude", "CLAUDE.md"),
                   "rb").read()
        self.assertIn(b"caf\xe9 notes", raw)  # byte round-trip preserved
        self.assertIn(b"## Agent working memory", raw)

    def test_codex_single_line_strings_and_user_comments_survive(self):
        # single-line strings containing ''' / # must not confuse the TOML
        # scanner, and user comments mentioning agent-skills must survive
        os.makedirs(os.path.join(self.home, ".codex"))
        with open(os.path.join(self.home, ".codex", "config.toml"), "w") as f:
            f.write("# NOTE TO SELF: my agent-skills clone lives in"
                    " ~/projects/agent-skills\n"
                    "note = 'use \"\"\" for multiline strings in TOML'\n"
                    'other = "a # not a comment"\n'
                    "[mcp_servers.db]\n"
                    "# this server is unrelated to agent-skills\n"
                    'command = "run-db"\n')
        self.install()
        self.install()
        toml = open(os.path.join(self.home, ".codex", "config.toml")).read()
        self.assertIn("NOTE TO SELF", toml)
        self.assertIn("unrelated to agent-skills", toml)
        self.assertIn("[mcp_servers.db]", toml)
        self.assertEqual(toml.count("hook codex session-start"), 1)

    def test_headingless_trailing_notes_survive_reinstall(self):
        self.install()
        md_path = os.path.join(self.home, ".claude", "CLAUDE.md")
        with open(md_path, "a") as f:
            f.write("\nremember: the staging API key rotates on fridays\n")
        self.install()
        md = open(md_path).read()
        self.assertIn("staging API key", md)
        self.assertEqual(md.count("## Agent working memory"), 1)

    def test_symlinked_settings_preserved(self):
        dotfiles = os.path.join(self.home, "dotfiles")
        os.makedirs(dotfiles)
        real = os.path.join(dotfiles, "claude-settings.json")
        with open(real, "w") as f:
            json.dump({"model": "opus"}, f)
        os.makedirs(os.path.join(self.home, ".claude"))
        link = os.path.join(self.home, ".claude", "settings.json")
        os.symlink(real, link)
        self.install()
        self.assertTrue(os.path.islink(link))
        cfg = json.load(open(real))
        self.assertIn("hooks", cfg)


class TestNudge(Base):
    """Mid-turn staleness nudge: the advisory stage injected at post-tool
    (the stop hook remains the blocking stage)."""

    KEY = "claude-claude-cl-sess-1"  # placeholder; real key set in helpers

    def edit(self, i, env=None, extra=None):
        p = {"tool_name": "Edit", "tool_input": {"file_path": "/x/f%d.c" % i}}
        p.update(extra or {})
        return self.hook("claude", "post-tool", self.claude_payload(p),
                         env=env)

    def expire_guards(self, key, minutes=10):
        """Session-start stamps last_inject, which deliberately blacks out
        nudges for one cooldown window — tests time-travel past it (and past
        any prior nudge/stop-block stamps)."""
        sdir = self.session_dir(key)
        mp = os.path.join(sdir, "meta.json")
        with open(mp) as f:
            meta = json.load(f)
        old = agent_memory.iso(time.time() - minutes * 60)
        for k in ("last_inject", "last_nudge"):
            if meta.get(k):
                meta[k]["ts"] = old
        if meta.get("last_stop_block"):
            meta["last_stop_block"] = old
        with open(mp, "w") as f:
            json.dump(meta, f)
        return sdir

    def start_stale(self, key="claude-cl-sess-1"):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state(key)
        sdir = self.session_dir(key)
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        self.expire_guards(key)
        return sdir

    def ctx(self, out):
        return out["hookSpecificOutput"]["additionalContext"]

    def nudge_journal_count(self, key):
        sdir = self.session_dir(key)
        j = open(os.path.join(sdir, "journal.jsonl")).read()
        return j.count('"ev": "nudge"')

    def test_fires_at_threshold_boundary(self):
        self.start_stale()
        outs = [self.edit(i) for i in range(5)]
        for out in outs[:4]:
            self.assertIsNone(out)  # n=4 stays silent: threshold is 5
        ctx = self.ctx(outs[4])
        self.assertIn("5 file-modifying tool calls", ctx)
        self.assertIn("state.md", ctx)
        self.assertIn("No need to mention this", ctx)
        meta = json.load(open(os.path.join(
            self.session_dir("claude-cl-sess-1"), "meta.json")))
        self.assertEqual(meta["last_nudge"]["count"], 1)
        self.assertEqual(meta["last_nudge"]["uncheckpointed"], 5)
        self.assertEqual(self.nudge_journal_count("claude-cl-sess-1"), 1)

    def test_cooldown_suppresses_then_escalates(self):
        self.start_stale()
        for i in range(5):
            out = self.edit(i)
        self.assertIsNotNone(out)
        self.assertIsNone(self.edit(5))  # inside cooldown
        self.expire_guards("claude-cl-sess-1")
        out2 = self.edit(6)
        self.assertIn("earlier reminder", self.ctx(out2))
        meta = json.load(open(os.path.join(
            self.session_dir("claude-cl-sess-1"), "meta.json")))
        self.assertEqual(meta["last_nudge"]["count"], 2)

    def test_checkpoint_resets_escalation(self):
        self.start_stale()
        for i in range(5):
            self.edit(i)
        # model complies, then goes stale again later
        self.write_state("claude-cl-sess-1", now="checkpointed")
        sdir = self.session_dir("claude-cl-sess-1")
        mid = time.time() - 300
        os.utime(os.path.join(sdir, "state.md"), (mid, mid))
        self.expire_guards("claude-cl-sess-1")  # nudge stamp older than state
        out = self.edit(5)  # already past threshold: fires immediately
        self.assertIsNotNone(out)
        self.assertNotIn("earlier reminder", self.ctx(out))
        meta = json.load(open(os.path.join(sdir, "meta.json")))
        self.assertEqual(meta["last_nudge"]["count"], 1)

    def test_episode_cap_two_reminders_then_silence(self):
        self.start_stale()
        for i in range(5):
            self.edit(i)
        self.expire_guards("claude-cl-sess-1")
        self.assertIsNotNone(self.edit(5))  # second reminder
        self.expire_guards("claude-cl-sess-1")
        self.assertIsNone(self.edit(6))  # episode cap: stop is level 3
        self.assertEqual(self.nudge_journal_count("claude-cl-sess-1"), 2)

    def test_checkpoint_write_itself_never_nudges(self):
        self.start_stale()
        for i in range(4):
            self.edit(i)
        sdir = self.session_dir("claude-cl-sess-1")
        sp = os.path.join(sdir, "state.md")
        out = self.hook("claude", "post-tool", self.claude_payload(
            {"tool_name": "Edit", "tool_input": {"file_path": sp}}))
        self.assertIsNone(out)  # store write is the checkpoint, not work
        out = self.hook("claude", "post-tool", self.claude_payload(
            {"tool_name": "Bash",
             "tool_input": {"command": "cat > %s <<'EOF'\nx\nEOF" % sp}}))
        self.assertIsNone(out)

    def test_subagent_tools_journal_but_never_nudge(self):
        self.start_stale()
        for i in range(4):
            self.edit(i)
        out = self.edit(4, extra={"agent_id": "a1",
                                  "agent_type": "general-purpose"})
        self.assertIsNone(out)  # crossed threshold, but inside a subagent
        out = self.edit(5)  # parent's next own tool call gets the nudge
        self.assertIn("6 file-modifying", self.ctx(out))

    def test_subagent_posttool_does_not_consume_reinject(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        mp = os.path.join(sdir, "meta.json")
        meta = json.load(open(mp))
        meta["last_event_ts"] = "2026-01-01T00:00:00.000Z"  # trip gap detector
        with open(mp, "w") as f:
            json.dump(meta, f)
        out = self.edit(0, extra={"agent_id": "a1"})
        self.assertIsNone(out)  # armed by the gap, but not spent on a subagent
        out = self.hook("claude", "post-tool", self.claude_payload(
            {"tool_name": "Read", "tool_input": {"file_path": "/x"}}))
        self.assertIn("context recovery", self.ctx(out))

    def test_blackout_after_session_start(self):
        # No expire_guards: last_inject is seconds old, so the whole burst
        # stays silent — the state file was literally just delivered.
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(8):
            self.assertIsNone(self.edit(i))

    def test_disabled_by_env(self):
        self.start_stale()
        env = {"AGENT_MEMORY_NUDGE_TOOLS": "0"}
        for i in range(8):
            self.assertIsNone(self.edit(i, env=env))

    def test_template_state_nudges_at_two(self):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        sdir = self.session_dir("claude-cl-sess-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        self.expire_guards("claude-cl-sess-1")
        self.assertIsNone(self.edit(0))
        out = self.edit(1)  # first checkpoint is the highest-value one
        self.assertIn("2 file-modifying", self.ctx(out))

    def test_nonmutating_tools_never_nudge(self):
        self.start_stale()
        for i in range(8):
            out = self.hook("claude", "post-tool", self.claude_payload(
                {"tool_name": "Read", "tool_input": {"file_path": "/x%d" % i}}))
            self.assertIsNone(out)

    def test_cursor_and_copilot_render_shapes(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        sdir = self.session_dir("cursor-cur-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        self.expire_guards("cursor-cur-1")
        for i in range(5):
            out = self.hook("cursor", "post-tool",
                            {"conversation_id": "cur-1",
                             "workspace_roots": [self.proj],
                             "tool_name": "Shell",
                             "tool_input": {"command": "make %d" % i}})
        self.assertIn("additional_context", out)

        self.hook("copilot", "session-start",
                  {"sessionId": "cop-1", "cwd": self.proj})
        self.write_state("copilot-cop-1")
        sdir = self.session_dir("copilot-cop-1")
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        self.expire_guards("copilot-cop-1")
        for i in range(5):
            out = self.hook("copilot", "post-tool",
                            {"sessionId": "cop-1", "cwd": self.proj,
                             "toolName": "create",
                             "toolArgs": json.dumps({"path": "/y%d" % i})})
        self.assertIn("additionalContext", out)

    def test_stop_still_blocks_after_ignored_nudge(self):
        self.start_stale()
        for i in range(5):
            self.edit(i)
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertEqual(out["decision"], "block")
        # nudge journal rows must not inflate the staleness count
        self.assertIn("5 action(s)", out["reason"])

    def test_soft_mode_nudges_with_truthful_escalation(self):
        env = {"AGENT_MEMORY_ENFORCE": "soft"}
        self.start_stale()
        for i in range(5):
            out = self.edit(i, env=env)
        self.assertIsNotNone(out)
        self.expire_guards("claude-cl-sess-1")
        ctx = self.ctx(self.edit(6, env=env))
        self.assertIn("recoverable", ctx)  # soft mode: no stop block to promise
        self.assertNotIn("forced at end of turn", ctx)

    def write_journal_tools(self, key, recs):
        """Overwrite the journal's tool lines with a crafted sequence.

        recs: list of (ts_offset_s, tool, target-or-None). Duplicate hook
        processes interleave with their originals, which subprocess timing
        can't reproduce reliably — direct construction can.
        """
        sdir = self.session_dir(key)
        base = time.time() - 60
        lines = []
        for off, tool, target in recs:
            rec = {"ts": agent_memory.iso(base + off), "ev": "tool",
                   "tool": tool}
            if target is not None:
                rec["target"] = target
            lines.append(json.dumps(rec))
        with open(os.path.join(sdir, "journal.jsonl"), "w") as f:
            f.write("\n".join(lines) + "\n")
        return sdir

    def test_double_fired_events_deduped(self):
        # A double-registered hook (codex config.toml + hooks.json) fires
        # twice per tool, near-simultaneously and interleaved; counts and
        # messages must reflect real activity.
        self.start_stale()
        recs = []
        for i in range(4):
            recs.append((i, "Edit", "/x/f%d.c" % i))
            recs.append((i + 0.05, "Edit", "/x/f%d.c" % i))  # the double-fire
        self.write_journal_tools("claude-cl-sess-1", recs)
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIn("4 action(s)", out["reason"])

    def test_real_work_within_window_still_counts(self):
        # Batched same-file edits land close together but are separate
        # journal-visible completions >=0.5s apart — must NOT collapse
        # (collapsing real work silently disarms the stop block).
        self.start_stale()
        recs = [(i * 0.6, "Edit", "/x/same.c") for i in range(4)]
        self.write_journal_tools("claude-cl-sess-1", recs)
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIn("4 action(s)", out["reason"])

    def test_targetless_tools_never_collapse(self):
        # Distinct NotebookEdit/MCP calls share (tool, None) — collapsing
        # them would erase real work, so target-less records never dedup.
        self.start_stale()
        recs = [(i * 0.05, "NotebookEdit", None) for i in range(4)]
        self.write_journal_tools("claude-cl-sess-1", recs)
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertIn("4 action(s)", out["reason"])

    def test_recent_stop_block_suppresses_nudge(self):
        self.start_stale()
        for i in range(3):  # stale for the stop, still under nudge threshold
            self.assertIsNone(self.edit(i))
        out = self.hook("claude", "stop",
                        self.claude_payload({"stop_hook_active": False}))
        self.assertEqual(out["decision"], "block")  # stamps last_stop_block
        for i in range(3, 9):  # well past threshold, inside cooldown
            self.assertIsNone(self.edit(i))
        self.expire_guards("claude-cl-sess-1")
        self.assertIsNotNone(self.edit(9))

    def set_stop_block(self, key, minutes_ago, pending=False):
        sdir = self.session_dir(key)
        mp = os.path.join(sdir, "meta.json")
        meta = json.load(open(mp))
        meta["last_stop_block"] = agent_memory.iso(
            time.time() - minutes_ago * 60)
        if pending:
            meta["stop_block_pending"] = True
        else:
            meta.pop("stop_block_pending", None)
        with open(mp, "w") as f:
            json.dump(meta, f)

    def escalate(self, key="claude-cl-sess-1"):
        """First nudge, then guards expired so the next edit escalates."""
        self.start_stale(key)
        for i in range(5):
            out = self.edit(i)
        self.assertIsNotNone(out)
        self.expire_guards(key)

    def test_escalation_inside_block_window_stays_truthful(self):
        # 10 min since the last stop block: the 30-min rate limit means the
        # stop hook will NOT block again — the text must not promise it.
        self.escalate()
        self.set_stop_block("claude-cl-sess-1", minutes_ago=10)
        ctx = self.ctx(self.edit(6))
        self.assertIn("earlier reminder", ctx)
        self.assertIn("recoverable", ctx)
        self.assertNotIn("forced at end of turn", ctx)

    def test_escalation_outside_block_window_promises_block(self):
        self.escalate()
        self.set_stop_block("claude-cl-sess-1", minutes_ago=40)
        ctx = self.ctx(self.edit(6))
        self.assertIn("forced at end of turn", ctx)

    def test_escalation_in_forced_continuation_stays_truthful(self):
        # Inside a forced continuation the eventual stop arrives with
        # stop_hook_active and is never blocked — even past the 30-min
        # window the text must not promise a block.
        self.escalate()
        self.set_stop_block("claude-cl-sess-1", minutes_ago=40, pending=True)
        ctx = self.ctx(self.edit(6))
        self.assertIn("recoverable", ctx)
        self.assertNotIn("forced at end of turn", ctx)


class TestBreadcrumbs(Base):
    """Journal-tail digest delivered wherever a stale state file is shown."""

    def stale_claude_session(self, n_tools=3):
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        self.write_state("claude-cl-sess-1")
        sdir = self.session_dir("claude-cl-sess-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(n_tools):
            self.hook("claude", "post-tool", self.claude_payload(
                {"tool_name": "Edit",
                 "tool_input": {"file_path": "/x/f%d.c" % i}}))
        return sdir

    def test_stale_resume_includes_tool_tail(self):
        self.stale_claude_session()
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "resume"}))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Uncheckpointed activity", ctx)
        self.assertIn("/x/f2.c", ctx)

    def test_fresh_resume_has_no_tail(self):
        self.stale_claude_session()
        self.write_state("claude-cl-sess-1", now="checkpointed")
        out = self.hook("claude", "session-start",
                        self.claude_payload({"source": "resume"}))
        self.assertNotIn("Uncheckpointed activity",
                         out["hookSpecificOutput"]["additionalContext"])

    def test_reinject_includes_tool_tail(self):
        self.hook("cursor", "session-start",
                  {"conversation_id": "cur-1", "workspace_roots": [self.proj]})
        self.write_state("cursor-cur-1")
        sdir = self.session_dir("cursor-cur-1")
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(3):
            self.hook("cursor", "post-tool",
                      {"conversation_id": "cur-1",
                       "workspace_roots": [self.proj], "tool_name": "Shell",
                       "tool_input": {"command": "make %d" % i}})
        self.hook("cursor", "pre-compact",
                  {"conversation_id": "cur-1",
                   "workspace_roots": [self.proj], "trigger": "auto"})
        out = self.hook("cursor", "post-tool",
                        {"conversation_id": "cur-1",
                         "workspace_roots": [self.proj], "tool_name": "Read",
                         "tool_input": {"file_path": "/x"}})
        ctx = out["additional_context"]
        self.assertIn("context recovery", ctx)
        self.assertIn("Uncheckpointed activity", ctx)
        self.assertIn("make 2", ctx)

    def test_candidates_offer_includes_tool_tail(self):
        # The fresh-session offer is the one delivery Cursor actually gets.
        self.stale_claude_session()
        out = self.hook("cursor", "session-start",
                        {"conversation_id": "cur-2",
                         "workspace_roots": [self.proj]})
        ctx = out["additional_context"]
        self.assertIn("Unfinished work found", ctx)
        self.assertIn("Uncheckpointed activity", ctx)
        self.assertIn("/x/f2.c", ctx)

    def test_breadcrumbs_trim_before_state_body(self):
        # Oversized state + stale journal tail: the combined text is
        # truncated as one string with crumbs LAST, so the body's head
        # survives and the digest is what disappears — never the reverse.
        self.hook("codex", "session-start",
                  {"session_id": "cx-1", "cwd": self.proj})
        sdir = self.session_dir("codex-cx-1")
        body = ("# Working state\nStatus: in-progress\n## Objective\n"
                "OBJECTIVE-MARKER\n" + ("x" * 250 + "\n") * 24)  # ~6KB
        with open(os.path.join(sdir, "state.md"), "w") as f:
            f.write(body)
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(3):
            self.hook("codex", "post-tool",
                      {"session_id": "cx-1", "cwd": self.proj,
                       "tool_name": "Edit",
                       "tool_input": {"file_path": "/x/f%d.c" % i}})
        out = self.hook("codex", "session-start",
                        {"session_id": "cx-1", "cwd": self.proj})
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(ctx.encode()), 6000)
        self.assertIn("OBJECTIVE-MARKER", ctx)  # body head survived
        self.assertNotIn("Uncheckpointed activity", ctx)  # crumbs trimmed

    def test_candidates_offer_respects_agent_budget(self):
        # Fresh-session offer: preview (<4KB) + breadcrumbs + head/rules can
        # exceed codex's 6KB budget; the whole message is capped.
        self.hook("claude", "session-start",
                  self.claude_payload({"source": "startup"}))
        sdir = self.write_state("claude-cl-sess-1")
        body = ("# Working state\nStatus: in-progress\n## Objective\nbig\n"
                + ("y" * 250 + "\n") * 15)  # ~3.8KB: preview still inlined
        with open(os.path.join(sdir, "state.md"), "w") as f:
            f.write(body)
        old = time.time() - 3600
        os.utime(os.path.join(sdir, "state.md"), (old, old))
        for i in range(8):
            self.hook("claude", "post-tool", self.claude_payload(
                {"tool_name": "Edit",
                 "tool_input": {"file_path": "/very/long/path/%s/f%d.c"
                                % ("z" * 90, i)}}))
        out = self.hook("codex", "session-start",
                        {"session_id": "cx-2", "cwd": self.proj})
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Unfinished work found", ctx)
        self.assertLessEqual(len(ctx.encode()), 6000)

    def test_codex_inject_budget_tighter_than_claude(self):
        big = "x" * 250
        for agent, sid in (("codex", "cx-1"), ("claude", "cl-sess-1")):
            payload = ({"session_id": sid, "cwd": self.proj}
                       if agent == "codex" else self.claude_payload())
            self.hook(agent, "session-start", dict(payload, source="startup"))
            sdir = self.session_dir("%s-%s" % (agent, sid))
            lines = ["# Working state", "Status: in-progress", "## Objective"]
            lines += [big] * 40  # ~10KB body
            with open(os.path.join(sdir, "state.md"), "w") as f:
                f.write("\n".join(lines))
        codex_out = self.hook("codex", "session-start",
                              {"session_id": "cx-1", "cwd": self.proj})
        claude_out = self.hook("claude", "session-start",
                               self.claude_payload({"source": "resume"}))
        codex_ctx = codex_out["hookSpecificOutput"]["additionalContext"]
        claude_ctx = claude_out["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(codex_ctx.encode()), 6000)
        self.assertGreater(len(claude_ctx.encode()), len(codex_ctx.encode()))


if __name__ == "__main__":
    unittest.main()

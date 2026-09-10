from contextlib import redirect_stderr
import copy
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/watch-pr/scripts/observe_pr.py"
FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
SPEC = importlib.util.spec_from_file_location("observe_pr", SCRIPT)
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)

PR = {
    "html_url": "https://github.com/example/project/pull/42",
    "number": 42, "state": "open", "merged": False, "draft": False,
    "title": "Example change", "body": "The intended behavior.",
    "mergeable": True, "mergeable_state": "clean", "updated_at": "2026-09-07T00:00:00Z",
    "head": {"sha": "abc", "ref": "feature", "repo": {"full_name": "example/project"}},
    "base": {"sha": "def", "ref": "main", "repo": {"full_name": "example/project"}},
    "merge_commit_sha": "merged-test", "labels": [], "requested_reviewers": [],
    "requested_teams": [],
}
CHECK = {
    "id": 7, "name": "tests", "status": "completed", "conclusion": "success",
    "html_url": "https://github.com/example/project/actions/runs/7",
}
RUN = {
    "id": 100, "name": "CI", "status": "completed", "conclusion": "failure",
    "html_url": "https://github.com/example/project/actions/runs/100",
}
STATUS = {"id": 12, "state": "error", "context": "external", "target_url": "https://ci.example/job/12"}


def sources():
    return {"pr": observer.pr_metadata(copy.deepcopy(PR)), "checks:abc": [copy.deepcopy(CHECK)],
            "discussion": [{"id": 10, "body": "Performance: unchanged"}]}


class ObservationTests(unittest.TestCase):
    def test_green_ci_does_not_hide_conflicts(self):
        data = sources()
        data["pr"].update(mergeable=False, mergeable_state="dirty")
        summary = observer.summarize(data)
        self.assertTrue(summary["github_ci_terminal"])
        self.assertIs(summary["mergeable"], False)
        self.assertEqual(summary["mergeable_state"], "dirty")

    def test_empty_checks_are_not_terminal_evidence(self):
        self.assertFalse(observer.summarize({"pr": observer.pr_metadata(PR)})["github_ci_terminal"])

    def test_missing_conclusion_and_pending_status_are_incomplete(self):
        data = sources()
        data["checks:abc"][0]["conclusion"] = None
        self.assertFalse(observer.summarize(data)["github_ci_terminal"])
        data = sources()
        data["statuses:abc"] = [dict(STATUS, state="pending")]
        self.assertFalse(observer.summarize(data)["github_ci_terminal"])

    def test_cancelled_check_remains_a_failure(self):
        data = sources()
        data["checks:abc"][0]["conclusion"] = "cancelled"
        summary = observer.summarize(data)
        self.assertTrue(summary["github_ci_terminal"])
        self.assertEqual(summary["failures"][0]["outcome"], "cancelled")

    def test_status_error_is_a_failure_with_its_context_and_link(self):
        data = sources()
        data["statuses:abc"] = [copy.deepcopy(STATUS)]
        failure = observer.summarize(data)["failures"][0]
        self.assertEqual((failure["level"], failure["name"], failure["url"]),
                         ("status", "external", "https://ci.example/job/12"))

    def test_stale_conclusion_on_an_unfinished_row_is_not_a_failure(self):
        data = sources()
        data["checks:abc"][0].update(status="queued", conclusion="failure")
        summary = observer.summarize(data)
        self.assertFalse(summary["github_ci_terminal"])
        self.assertEqual(summary["failures"], [])

    def test_action_required_is_reported_apart_from_failures(self):
        data = sources()
        data["workflows:abc"] = [dict(RUN, conclusion="action_required")]
        del data["checks:abc"]
        summary = observer.summarize(data)
        self.assertTrue(summary["github_ci_terminal"])
        self.assertEqual(summary["failures"], [])
        self.assertEqual(summary["action_required"][0]["outcome"], "action_required")

    def test_successful_job_cannot_hide_workflow_blockers(self):
        for status, conclusion, bucket in [("in_progress", None, "pending"),
                                           ("completed", "failure", "failures"),
                                           ("completed", "action_required", "action_required")]:
            with self.subTest(conclusion=conclusion):
                data = sources()
                data["workflows:abc"] = [dict(RUN, status=status, conclusion=conclusion)]
                summary = observer.summarize(data)
                self.assertEqual(summary["github_ci_rows"], 2)
                self.assertEqual(summary["github_ci_terminal"], status == "completed")
                self.assertEqual(summary[bucket][0]["level"], "run")

    def test_new_run_supersedes_only_its_own_old_suite(self):
        old = dict(RUN, workflow_id=1, event="pull_request", head_branch="feature", check_suite_id=10)
        new = dict(old, id=101, status="queued", conclusion=None, check_suite_id=11)
        other = dict(old, id=102, workflow_id=2, check_suite_id=12)
        data = sources()
        data["workflows:abc"] = [old, new, other]
        data["checks:abc"] = [dict(CHECK, conclusion="failure", check_suite={"id": 10})]
        summary = observer.summarize(data)
        self.assertFalse(summary["github_ci_terminal"])
        self.assertEqual([row["id"] for row in summary["pending"]], [101])
        self.assertEqual([row["id"] for row in summary["failures"]], [102])

    def test_latest_attempt_and_distinct_workflow_events_are_retained(self):
        old = dict(RUN, workflow_id=1, event="pull_request", run_attempt=1)
        new = dict(old, run_attempt=2, status="in_progress", conclusion=None)
        push = dict(old, id=101, event="push")
        selected = observer.current_runs([new, old, push])
        self.assertEqual([(r["id"], r["run_attempt"]) for r in selected], [(100, 2), (101, 1)])

    def test_dispatches_and_forks_are_not_treated_as_reruns(self):
        for event in ("workflow_dispatch", "pull_request"):
            with self.subTest(event=event):
                old = dict(RUN, workflow_id=1, event=event, head_branch="feature", head_repository={"id": 1})
                new = dict(old, id=101, head_repository={"id": 2} if event == "pull_request" else {"id": 1})
                self.assertEqual(len(observer.current_runs([old, new])), 2)

    def test_runs_for_different_prs_are_not_superseded(self):
        old = dict(RUN, workflow_id=1, event="pull_request", pull_requests=[{"id": 1}])
        new = dict(old, id=101, pull_requests=[{"id": 2}])
        self.assertEqual(len(observer.current_runs([old, new])), 2)

    def test_missing_required_check_is_visible_despite_other_successes(self):
        data = sources()
        data["requirements"] = {"head": "abc", "base": "def", "test_merge_sha": "merged-test",
                                "checks": [{"source": "checks:abc", "name": "build"}]}
        summary = observer.summarize(data)
        self.assertTrue(summary["requirements_current"])
        self.assertEqual(summary["missing_required"], data["requirements"]["checks"])

    def test_requirements_distinguish_sha_kind_and_app(self):
        data = sources()
        data["checks:abc"][0]["app"] = {"id": 42}
        checks = [{"source": "checks:abc", "name": "tests", "app_id": 42},
                  {"source": "statuses:abc", "name": "tests"},
                  {"source": "checks:merged-test", "name": "tests"},
                  {"source": "checks:abc", "name": "tests", "app_id": 43}]
        data["requirements"] = {"head": "abc", "base": "def", "test_merge_sha": "merged-test", "checks": checks}
        self.assertEqual(observer.summarize(data)["missing_required"], checks[1:])

    def test_requirements_must_match_all_revisions(self):
        data = sources()
        self.assertFalse(observer.summarize(data)["requirements_current"])
        expected = {"head": "abc", "base": "def", "test_merge_sha": "merged-test", "checks": []}
        for key in ("head", "base", "test_merge_sha"):
            data["requirements"] = {**expected, key: "stale"}
            self.assertFalse(observer.summarize(data)["requirements_current"])

    def test_skips_are_visible_for_coverage_review(self):
        data = sources()
        data["checks:abc"][0]["conclusion"] = "skipped"
        self.assertEqual(observer.summarize(data)["skipped"][0]["name"], "tests")

    def test_pagination_retains_later_pages(self):
        first = [{"id": n} for n in range(100)]
        pages = [{"total_count": 101, "check_runs": first},
                 {"total_count": 101, "check_runs": [{"id": 100}]}]
        with patch.object(observer, "github", return_value=pages):
            rows = observer.paginated("github.com", "checks", "check_runs")
        self.assertEqual(len(rows), 101)
        self.assertEqual(rows[-1]["id"], 100)

    def test_changing_pagination_is_a_retriable_race(self):
        with patch.object(observer, "github", return_value=[{"total_count": 2, "statuses": []}]):
            with self.assertRaises(observer.ObservationChanged):
                observer.paginated("github.com", "statuses", "statuses")

    def test_pagination_race_is_retried_by_observe_settled(self):
        calls = []

        def listing(host, endpoint, key=None):
            calls.append(endpoint)
            if len(calls) == 1:
                raise observer.ObservationChanged("Listing changed while paginating")
            return []

        with patch.object(observer, "github", return_value=PR), \
                patch.object(observer, "paginated", side_effect=listing):
            data = observer.observe_settled(PR["html_url"])
        self.assertIn("checks:abc", data)
        self.assertEqual(len(calls), 10)

    def test_api_uses_get_and_propagates_failures(self):
        failure = subprocess.CalledProcessError(1, ["gh"], stderr="API unavailable")
        with patch.object(observer.subprocess, "run", side_effect=failure) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                observer.github("github.com", "repos/example/project/pulls/42", paginate=True)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--method") + 1], "GET")
        self.assertIn("--paginate", command)
        self.assertIn("--slurp", command)

    def test_head_changes_invalidate_the_observation(self):
        moved = copy.deepcopy(PR)
        moved["head"]["sha"] = "new-head"
        with patch.object(observer, "github", side_effect=[PR, moved]), \
                patch.object(observer, "paginated", return_value=[]):
            with self.assertRaisesRegex(ValueError, "PR revision or mergeability changed"):
                observer.observe(PR["html_url"])

    def test_comment_churn_during_collection_is_not_a_race(self):
        churned = dict(PR, updated_at="2026-09-07T00:05:00Z", body="Edited.")
        with patch.object(observer, "github", side_effect=[PR, churned]), \
                patch.object(observer, "paginated", return_value=[]):
            data = observer.observe(PR["html_url"])
        self.assertEqual(data["pr"]["body"], "The intended behavior.")

    def test_collection_race_is_retried_then_settles(self):
        settled = {"pr": observer.pr_metadata(PR)}
        with patch.object(observer, "observe",
                          side_effect=[observer.ObservationChanged("moved"), settled]) as observe:
            self.assertIs(observer.observe_settled(PR["html_url"]), settled)
        self.assertEqual(observe.call_count, 2)

    def test_persistent_collection_race_propagates(self):
        with patch.object(observer, "observe",
                          side_effect=observer.ObservationChanged("moved")) as observe:
            with self.assertRaisesRegex(ValueError, "moved"):
                observer.observe_settled(PR["html_url"], attempts=3)
        self.assertEqual(observe.call_count, 3)

    def test_observes_head_and_test_merge_with_review_sources(self):
        with patch.object(observer, "github", return_value=PR), \
                patch.object(observer, "paginated", return_value=[]) as pages:
            data = observer.observe(PR["html_url"])
        self.assertEqual(sorted(data), ["checks:abc", "checks:merged-test", "discussion", "pr", "review_comments",
                                        "reviews", "statuses:abc", "statuses:merged-test", "workflows:abc", "workflows:merged-test"])
        self.assertEqual(data["pr"]["test_merge_sha"], "merged-test")
        self.assertEqual(pages.call_count, 9)

    def test_base_and_mergeability_changes_invalidate_collection(self):
        for change in ("base", "mergeability", "test_merge", "retarget"):
            with self.subTest(change=change):
                moved = copy.deepcopy(PR)
                if change == "base":
                    moved["base"]["sha"] = "new-base"
                elif change == "retarget":
                    moved["base"]["ref"] = "release"
                elif change == "test_merge":
                    moved["merge_commit_sha"] = "new-merge"
                else:
                    moved.update(mergeable=False, mergeable_state="dirty")
                with patch.object(observer, "github", side_effect=[PR, moved]), \
                        patch.object(observer, "paginated", return_value=[]):
                    with self.assertRaises(observer.ObservationChanged):
                        observer.observe(PR["html_url"])

    def test_merge_only_failure_is_reported(self):
        def listing(host, endpoint, key=None):
            return [dict(CHECK, conclusion="failure")] if "commits/merged-test/check-runs" in endpoint else []
        with patch.object(observer, "github", return_value=PR), \
                patch.object(observer, "paginated", side_effect=listing):
            data = observer.observe(PR["html_url"])
        self.assertEqual(observer.summarize(data)["failures"][0]["source"], "checks:merged-test")

    def test_closed_pr_still_collects_head_ci(self):
        closed = dict(PR, state="closed", merged=True)
        with patch.object(observer, "github", return_value=closed), \
                patch.object(observer, "paginated", return_value=[]):
            data = observer.observe(PR["html_url"])
        self.assertIn("checks:abc", data)
        self.assertIsNone(data["pr"]["test_merge_sha"])

    def test_unknown_mergeability_is_polled_before_collecting(self):
        cold = dict(PR, mergeable=None, mergeable_state="unknown", merge_commit_sha=None)
        with patch.object(observer, "github", side_effect=[cold, PR, PR]) as github, \
                patch.object(observer, "paginated", return_value=[]), \
                patch.object(observer.time, "sleep") as sleep:
            data = observer.observe(PR["html_url"])
        self.assertIs(data["pr"]["mergeable"], True)
        self.assertEqual(github.call_count, 3)
        sleep.assert_called_once_with(observer.MERGEABILITY_WAIT)

    def test_unknown_mergeability_is_recorded_when_it_never_settles(self):
        cold = dict(PR, mergeable=None, mergeable_state="unknown", merge_commit_sha=None)
        with patch.object(observer, "github", return_value=cold) as github, \
                patch.object(observer, "paginated", return_value=[]), \
                patch.object(observer.time, "sleep"):
            data = observer.observe(PR["html_url"])
        self.assertIsNone(observer.summarize(data)["mergeable"])
        self.assertEqual(github.call_count, observer.MERGEABILITY_POLLS + 1)

    def test_invalid_url_is_rejected_before_using_gh(self):
        with patch.object(observer, "github") as github:
            with self.assertRaises(ValueError):
                observer.observe("https://token@github.com/example/project/pull/42")
        github.assert_not_called()


class StateTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.state_dir = Path(self.scratch.name)

    def events(self):
        return [json.loads(line) for line in (self.state_dir / "events.jsonl").read_text().splitlines()]

    def test_restart_is_quiet_and_keeps_the_unprocessed_event(self):
        first = observer.record(self.state_dir, sources())
        second = observer.record(self.state_dir, sources())
        self.assertEqual(second["event"], "unchanged")
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        events = self.events()
        self.assertEqual(len(events), 1)
        for digest in events[0]["sources"].values():
            self.assertTrue((self.state_dir / "sources" / f"{digest}.json").is_file())

    def test_edited_comment_is_detected_without_a_new_id(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["discussion"][0]["body"] = "Performance: degradation"
        event = observer.record(self.state_dir, changed)
        self.assertEqual(event["changed"], ["discussion"])

    def test_only_changed_sources_get_new_files(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["discussion"][0]["body"] = "Performance: degradation"
        observer.record(self.state_dir, changed)
        self.assertEqual(len(list((self.state_dir / "sources").iterdir())), len(sources()) + 1)

    def test_rerun_with_the_same_check_name_is_detected(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["checks:abc"][0].update(id=8, conclusion="failure")
        event = observer.record(self.state_dir, changed)
        self.assertEqual(event["changed"], ["checks:abc"])
        self.assertEqual(event["failures"][0]["id"], 8)

    def test_return_to_an_earlier_value_is_a_new_event_with_the_same_id(self):
        first = observer.record(self.state_dir, sources())
        changed = sources()
        changed["pr"]["mergeable"] = False
        observer.record(self.state_dir, changed)
        recovered = observer.record(self.state_dir, sources())
        self.assertEqual(first["snapshot_id"], recovered["snapshot_id"])
        self.assertEqual(recovered["changed"], ["pr"])
        self.assertEqual(len(self.events()), 3)

    def test_replay_after_an_interrupted_write_repeats_the_snapshot_id(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["pr"]["mergeable"] = False
        with patch.object(observer, "replace_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                observer.record(self.state_dir, changed)
        replayed = observer.record(self.state_dir, changed)
        events = self.events()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[1]["snapshot_id"], events[2]["snapshot_id"])
        self.assertEqual(replayed["snapshot_id"], events[2]["snapshot_id"])
        self.assertEqual(len(list((self.state_dir / "sources").iterdir())), len(sources()) + 1)

    def test_invalid_data_does_not_replace_a_valid_snapshot(self):
        observer.record(self.state_dir, sources())
        latest = (self.state_dir / "latest.json").read_bytes()
        invalid = sources()
        del invalid["checks:abc"][0]["status"]
        with self.assertRaises(KeyError):
            observer.record(self.state_dir, invalid)
        self.assertEqual((self.state_dir / "latest.json").read_bytes(), latest)

    def test_other_pr_cannot_reuse_this_state(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["pr"]["html_url"] = "https://github.com/example/project/pull/43"
        with self.assertRaisesRegex(ValueError, "different PR"):
                observer.record(self.state_dir, changed)

    def test_timestamp_only_change_is_quiet_but_keeps_fresh_evidence(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["pr"]["updated_at"] = "2026-09-10T12:00:00Z"
        event = observer.record(self.state_dir, changed)
        self.assertEqual(event["event"], "unchanged")
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(json.loads(Path(event["sources"]["pr"]).read_text())["updated_at"],
                         changed["pr"]["updated_at"])

    def test_same_result_new_attempt_is_not_quiet(self):
        data = sources()
        data["workflows:abc"] = [dict(RUN, run_attempt=1)]
        observer.record(self.state_dir, data)
        data["workflows:abc"][0]["run_attempt"] = 2
        event = observer.record(self.state_dir, data)
        self.assertEqual(event["changed"], ["workflows:abc"])

    def test_corrupt_source_is_repaired_before_reporting_success(self):
        first = observer.record(self.state_dir, sources())
        path = Path(first["sources"]["checks:abc"])
        path.write_bytes(b'\xff{"id":')
        observer.record(self.state_dir, sources())
        self.assertEqual(json.loads(path.read_text()), sources()["checks:abc"])

    def test_interrupted_source_publication_can_be_retried(self):
        with patch.object(Path, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                observer.record(self.state_dir, sources())
        self.assertFalse((self.state_dir / "latest.json").exists())
        result = observer.record(self.state_dir, sources())
        self.assertTrue(all(json.loads(Path(path).read_text()) is not None for path in result["sources"].values()))

    def test_partial_event_tail_does_not_corrupt_replayed_event(self):
        observer.record(self.state_dir, sources())
        with (self.state_dir / "events.jsonl").open("ab") as output:
            output.write(b'{"event":' + b'x' * 5000)
        data = sources()
        data["pr"]["mergeable"] = False
        observer.record(self.state_dir, data)
        self.assertEqual(len(self.events()), 2)

    def test_compact_output_exposes_omitted_count_and_full_evidence(self):
        data = sources()
        data["checks:abc"] = [dict(CHECK, id=n, conclusion="failure") for n in range(25)]
        full = observer.record(self.state_dir, data)
        compact = observer.compact(full)
        self.assertEqual((compact["failures_count"], len(compact["failures"])), (25, 20))
        self.assertEqual(len(full["failures"]), 25)
        self.assertEqual(len(json.loads(Path(compact["sources"]["checks:abc"]).read_text())), 25)


class ProcessTests(unittest.TestCase):
    """Drive main() as a process, with a scripted `gh` on PATH."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.state_dir = root / "observer"
        self.gh_dir = root / "gh"
        self.gh_dir.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        shim = bin_dir / "gh"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_GH}" "$@"\n')
        shim.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                    "FAKE_GH_DIR": str(self.gh_dir)}

    def script(self, **responses):
        scripted = {"pulls/42": [PR], "issues/42/comments": [[]], "pulls/42/comments": [[]],
                    "pulls/42/reviews": [[]],
                    "commits/abc/check-runs": [{"total_count": 1, "check_runs": [CHECK]}],
                    "commits/abc/status": [{"total_count": 0, "statuses": []}],
                    "commits/merged-test/check-runs": [{"total_count": 0, "check_runs": []}],
                    "commits/merged-test/status": [{"total_count": 0, "statuses": []}],
                    "actions/runs": [{"total_count": 0, "workflow_runs": []}]}
        scripted.update(responses)
        (self.gh_dir / "responses.json").write_text(json.dumps(scripted))

    def run_observer(self, *flags):
        return subprocess.run(
            [sys.executable, str(SCRIPT), PR["html_url"], "--state-dir", str(self.state_dir), *flags],
            env=self.env, capture_output=True, text=True, timeout=60)

    def test_single_observation_prints_one_result(self):
        self.script()
        run = self.run_observer()
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual((result["event"], result["head"], result["github_ci_terminal"]),
                         ("changed", "abc", True))

    def test_process_reports_missing_requirement_and_persists_inventory(self):
        self.script()
        self.state_dir.mkdir()
        requirements = {"head": "abc", "base": "def", "test_merge_sha": "merged-test",
                        "checks": [{"source": "statuses:abc", "name": "CH Inc sync"}]}
        (self.state_dir / "requirements.json").write_text(json.dumps(requirements))
        run = self.run_observer()
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertTrue(result["requirements_current"])
        self.assertEqual(result["missing_required_count"], 1)
        self.assertEqual(json.loads(Path(result["sources"]["requirements"]).read_text()), requirements)

    def test_malformed_requirements_preserve_last_good_snapshot(self):
        self.script()
        self.assertEqual(self.run_observer().returncode, 0)
        latest = (self.state_dir / "latest.json").read_bytes()
        (self.state_dir / "requirements.json").write_text('["wrong shape"]')
        run = self.run_observer()
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stderr)["event"], "observation_error")
        self.assertEqual((self.state_dir / "latest.json").read_bytes(), latest)

    def test_watch_does_not_print_timestamp_only_polls(self):
        changed_time = dict(PR, updated_at="2026-09-10T12:00:00Z")
        closed = dict(changed_time, state="closed", merged=True)
        self.script(**{"pulls/42": [PR, PR, changed_time, changed_time, closed]})
        run = self.run_observer("--watch", "--interval", "1")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual([json.loads(line)["state"] for line in run.stdout.splitlines()], ["open", "closed"])

    def test_watch_prints_changes_and_stops_when_closed(self):
        closed = dict(PR, state="closed", merged=True)
        self.script(**{"pulls/42": [PR, PR, closed]})
        run = self.run_observer("--watch", "--interval", "1")
        self.assertEqual(run.returncode, 0, run.stderr)
        states = [json.loads(line)["state"] for line in run.stdout.splitlines()]
        self.assertEqual(states, ["open", "closed"])

    def test_watch_logs_a_transient_failure_and_keeps_polling(self):
        closed = dict(PR, state="closed", merged=True)
        self.script(**{"pulls/42": [PR, PR, {"fail": "gh: HTTP 502: Server Error"}, closed]})
        run = self.run_observer("--watch", "--interval", "1")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(run.stdout.splitlines()), 2)
        logged = [json.loads(line) for line in (self.state_dir / "events.jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in logged], ["changed", "observation_error", "changed"])
        self.assertIn("502", logged[1]["error"])
        self.assertIn("observation_error", run.stderr)

    def test_watch_gives_up_after_repeated_failures(self):
        failure = subprocess.CalledProcessError(1, ["gh"], stderr="gh: HTTP 502")
        argv = ["observe_pr.py", PR["html_url"], "--state-dir", str(self.state_dir), "--watch"]
        with patch.object(observer.sys, "argv", argv), patch.object(observer.time, "sleep") as sleep, \
                patch.object(observer.subprocess, "run", side_effect=failure), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                observer.main()
        logged = (self.state_dir / "events.jsonl").read_text().splitlines()
        self.assertEqual(len(logged), observer.MAX_CONSECUTIVE_ERRORS)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [120, 240, 360, 480])

    def test_gh_failure_in_single_mode_exits_with_an_error_envelope(self):
        self.script(**{"pulls/42": [{"fail": "gh: HTTP 502: Server Error"}]})
        run = self.run_observer()
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stdout, "")
        error = json.loads(run.stderr)
        self.assertEqual(error["event"], "observation_error")
        self.assertIn("502", error["error"])

    def test_second_watcher_exits_busy(self):
        self.script()
        self.state_dir.mkdir()
        with (self.state_dir / "watch.lock").open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run = self.run_observer("--watch", "--interval", "1")
        self.assertEqual(run.returncode, 3)
        self.assertEqual(json.loads(run.stderr)["event"], "observer_busy")

    def test_one_shot_waits_for_a_running_poll(self):
        self.script()
        self.state_dir.mkdir()
        held = (self.state_dir / "observer.lock").open("a")
        self.addCleanup(held.close)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        threading.Timer(2, fcntl.flock, [held, fcntl.LOCK_UN]).start()
        run = self.run_observer()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["event"], "changed")


if __name__ == "__main__":
    unittest.main()

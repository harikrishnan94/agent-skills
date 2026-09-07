import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/watch-pr/scripts/observe_pr.py"
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
        data["statuses:abc"] = [{"id": 12, "state": "pending", "context": "external",
                                 "target_url": "https://ci.example/job/12"}]
        self.assertFalse(observer.summarize(data)["github_ci_terminal"])

    def test_cancelled_check_remains_a_failure(self):
        data = sources()
        data["checks:abc"][0]["conclusion"] = "cancelled"
        summary = observer.summarize(data)
        self.assertTrue(summary["github_ci_terminal"])
        self.assertEqual(summary["failures"][0]["outcome"], "cancelled")

    def test_pagination_retains_later_pages(self):
        first = [{"id": n} for n in range(100)]
        pages = [{"total_count": 101, "check_runs": first},
                 {"total_count": 101, "check_runs": [{"id": 100}]}]
        with patch.object(observer, "github", return_value=pages):
            rows = observer.paginated("github.com", "checks", "check_runs")
        self.assertEqual(len(rows), 101)
        self.assertEqual(rows[-1]["id"], 100)

    def test_truncated_pagination_is_an_error(self):
        with patch.object(observer, "github", return_value=[{"total_count": 2, "statuses": []}]):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                observer.paginated("github.com", "statuses", "statuses")

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
            with self.assertRaisesRegex(ValueError, "PR changed"):
                observer.observe(PR["html_url"])

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
        self.assertIn("checks:abc", data)
        self.assertIn("checks:merged-test", data)
        self.assertIn("reviews", data)
        self.assertIn("review_comments", data)
        self.assertEqual(pages.call_count, 9)

    def test_unknown_mergeability_does_not_use_a_stale_merge_sha(self):
        unknown = copy.deepcopy(PR)
        unknown["mergeable"] = None
        with patch.object(observer, "github", return_value=unknown), \
                patch.object(observer, "paginated", return_value=[]):
            data = observer.observe(PR["html_url"])
        self.assertNotIn("checks:merged-test", data)
        self.assertIsNone(observer.summarize(data)["mergeable"])

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

    def test_restart_is_quiet_and_keeps_the_unprocessed_event(self):
        first = observer.record(self.state_dir, sources())
        second = observer.record(self.state_dir, sources())
        self.assertEqual(second["event"], "unchanged")
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        events = (self.state_dir / "events.jsonl").read_text().splitlines()
        self.assertEqual(len(events), 1)
        self.assertTrue(Path(json.loads(events[0])["snapshot"]).is_file())

    def test_edited_comment_is_detected_without_a_new_id(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["discussion"][0]["body"] = "Performance: degradation"
        event = observer.record(self.state_dir, changed)
        self.assertEqual(event["changed"], ["discussion"])

    def test_rerun_with_the_same_check_name_is_detected(self):
        observer.record(self.state_dir, sources())
        changed = sources()
        changed["checks:abc"][0].update(id=8, conclusion="failure")
        event = observer.record(self.state_dir, changed)
        self.assertEqual(event["changed"], ["checks:abc"])
        self.assertEqual(event["failures"][0]["id"], 8)

    def test_return_to_an_earlier_value_is_a_new_event(self):
        first = observer.record(self.state_dir, sources())
        changed = sources()
        changed["pr"]["mergeable"] = False
        observer.record(self.state_dir, changed)
        recovered = observer.record(self.state_dir, sources())
        self.assertNotEqual(first["snapshot_id"], recovered["snapshot_id"])
        self.assertEqual(recovered["changed"], ["pr"])

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


if __name__ == "__main__":
    unittest.main()

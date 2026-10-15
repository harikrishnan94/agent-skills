import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / "skills/review-pr"
SCRIPT = SKILL / "scripts/check_review.py"
SPEC = importlib.util.spec_from_file_location("check_review", SCRIPT)
check_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_review)

HEAD = "5932a65b5c9fc57deb6ba6fd0c6808dd5fbdc264"

GOOD = f"""## Fix HashJoin probe continuation materialization (#121209 by @namtran1812): Request changes
Request changes: it breaks `04102_hash_join_stress_test` and has no numbers behind the performance claim.
Head: {HEAD} (re-checked before presenting: unchanged)

### What it does
**1. Change and gain.** The probe keeps the rest of a left block inside `HashJoin`, so the copy goes away.
**2. Context.** `JoiningTransform` calls `HashJoin::joinBlock` once per left block.
**3. Problem.** Each round copies the remaining rows: 32,004,000 probe rows for the repro in #121165.
**4. Before → After.**

```text
before: JoiningTransform -> HashJoin -> rest of block copied -> HashJoin ...
after:  JoiningTransform -> HashJoin::ContinuationResult -> probe the rest in place   <N> rounds
```

Worked example: N = 8000, p = 1, so 8000 rounds and no copies.
**5. Promises and unchanged.** Same rows, same output block limit. `parallel_hash` is unchanged.
**6. How the code does it.** A wrapper result probes the leftover rows (`HashJoin::ContinuationResult`).
**7. Performance.** n/a: the author gave no numbers. Cost added: one allocation per block, like a `std::vector<int>` of selectors.
**8. Correctness and safety.** Every left row is probed once, in order.
**9. Interaction.** `GraceHashJoin` gets the change too.

### Findings
- **Blocking** CI is broken by the PR. Evidence: step 14 of `04102_hash_join_stress_test` fails in all four jobs.
- **Non-blocking** The tests check a counter, not rows.
  - Evidence: `04612` sends the output to `FORMAT Null`.

### Not raising
- `next()` after `is_last`: no caller does it.

### Draft review (event: REQUEST_CHANGES)
Body: Thanks for the PR, @namtran1812! Requesting changes, details inline. Main blocker is `04102_hash_join_stress_test`.
1. `tests/queries/0_stateless/04612_left_join_additional_filter_right_any_scatter.sql:45` `04102` still expects the re-probe, can we update it?
2. `src/Interpreters/HashJoin/HashJoin.cpp:1383` could you post before/after on the issue's repro?

### Review record
- **1. Gather:** done
  - Author: human, @namtran1812
  - Issues: #121165, #91664
  - CI caused by PR: `04102_hash_join_stress_test` in four jobs
  - Existing reviews: bots only, no blockers
  - Repo review skill: n/a: none in this repository
  - Overlapping PRs: #115605
- **2. Explain:** done
  - Parts n/a: 7 (the author gave no numbers)
- **3. Structural passes:** done
  - reduce-complexity: reported dead resubmit branches; kept as a finding
  - humanize: nothing to change
  - plain-prose: description has no numbers; dropped, covered by the performance ask
- **4. Evidence:** done
  - Performance: applied: no numbers, no perf test, grid of sizes requested
  - Correctness: applied: invariant is one probe per left row
  - Tests: applied: counter-only checks, FORMAT Null
  - Description: applied: grace_hash is not mentioned
  - Design and scope: n/a: no second implementation of an existing mechanism
- **5. Verify:** done
  - Re-checked at: {HEAD}
  - Challenger: confirmed the CI break, added that the split check is vacuous; dropped nothing
  - Conflicts: none
  - Labels: new regression: 04102 still asserts the old counter
- **6. Choose:** done
  - Row: CI broken by the PR
- **7. Draft:** done
  - Passes: hari-voice, plain-prose, humanize, comments.md
  - Greeting: human

Verification limits: traced the code at the pinned SHA, ran nothing.
"""


def problems_after(old, new, text=GOOD):
    assert old in text, f"fixture does not contain {old!r}"
    return check_review.check(text.replace(old, new, 1))


class CheckReviewTests(unittest.TestCase):
    def assertProblem(self, problems, fragment):
        self.assertTrue(
            any(fragment in problem for problem in problems),
            f"no problem mentions {fragment!r}; got {problems}",
        )

    def test_conforming_package_passes(self):
        self.assertEqual(check_review.check(GOOD), [])

    def test_template_in_skill_matches_the_checker(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"### 8\. Present and stop.*?```markdown\n(.*?)\n```", skill, re.S)
        self.assertIsNotNone(match, "step 8 template not found in SKILL.md")
        problems = check_review.check(match.group(1))
        structural = ("is missing", "unexpected heading", "out of order", "has no text",
                      "has no result", "needs a reason", "must be labelled",
                      "must be followed by")
        self.assertEqual(
            [p for p in problems if any(word in p for word in structural)], [],
            "SKILL.md's template and check_review.py disagree about the structure",
        )
        self.assertProblem(problems, "placeholder <title>")

    def test_review_record_removed(self):
        problems = check_review.check(GOOD.split("### Review record")[0])
        self.assertProblem(problems, "'### Review record' section is missing")

    def test_a_part_is_dropped(self):
        line = "**6. How the code does it.** A wrapper result probes the leftover rows (`HashJoin::ContinuationResult`).\n"
        self.assertProblem(problems_after(line, ""), "part '**6. How the code does it.**' is missing")

    def test_parts_out_of_order(self):
        two = "**2. Context.** `JoiningTransform` calls `HashJoin::joinBlock` once per left block.\n"
        three = "**3. Problem.** Each round copies the remaining rows: 32,004,000 probe rows for the repro in #121165.\n"
        swapped = GOOD.replace(two + three, three + two, 1)
        self.assertNotEqual(swapped, GOOD)
        self.assertProblem(check_review.check(swapped), "not in order 1 to 9")

    def test_empty_part_is_rejected(self):
        problems = problems_after("**9. Interaction.** `GraceHashJoin` gets the change too.", "**9. Interaction.**")
        self.assertProblem(problems, "part 9 (Interaction) has no text")

    def test_not_done_needs_incomplete_first_line(self):
        not_done = "- **3. Structural passes:** not done: reduce-complexity could not run"
        problems = problems_after("- **3. Structural passes:** done", not_done)
        self.assertProblem(problems, "must start with 'Incomplete: <steps>.'")
        fixed = GOOD.replace("- **3. Structural passes:** done", not_done, 1).replace(
            "Request changes: it breaks", "Incomplete: step 3. Request changes: it breaks", 1)
        self.assertEqual(check_review.check(fixed), [])

    def test_not_done_in_an_evidence_entry_also_counts(self):
        problems = problems_after(
            "  - Tests: applied: counter-only checks, FORMAT Null",
            "  - Tests: not done: no time to read the tests")
        self.assertProblem(problems, "must start with 'Incomplete: <steps>.'")

    def test_not_done_needs_a_reason(self):
        problems = problems_after("- **6. Choose:** done", "- **6. Choose:** not done")
        self.assertProblem(problems, "step 6 (Choose) is 'not done' and needs a reason")

    def test_event_must_match_verdict(self):
        problems = problems_after("(event: REQUEST_CHANGES)", "(event: APPROVE)")
        self.assertProblem(problems, "needs event REQUEST_CHANGES")

    def test_event_must_be_one_value(self):
        problems = problems_after("(event: REQUEST_CHANGES)", "(event: APPROVE | COMMENT | REQUEST_CHANGES)")
        self.assertProblem(problems, "'### Draft review (event: X)'")

    def test_both_approve_verdicts_map_to_approve(self):
        for verdict in ("Approve", "Approve with the suggestions"):
            text = GOOD.replace(": Request changes\n", f": {verdict}\n", 1).replace(
                "(event: REQUEST_CHANGES)", "(event: APPROVE)", 1)
            self.assertEqual(check_review.check(text), [], verdict)

    def test_invalid_verdict(self):
        self.assertProblem(problems_after(": Request changes\n", ": Looks fine\n"), "the first line must be")

    def test_leftover_placeholder(self):
        problems = problems_after("- `next()` after `is_last`: no caller does it.", "- `next()` after `is_last`: <reason>")
        self.assertProblem(problems, "placeholder <reason> is still there")

    def test_placeholder_inside_a_code_fence_is_ignored(self):
        self.assertEqual(check_review.check(GOOD), [])
        self.assertIn("<N>", GOOD)

    def test_other_angle_brackets_are_fine(self):
        self.assertIn("std::vector<int>", GOOD)
        self.assertEqual(check_review.check(GOOD), [])

    def test_missing_evidence_section(self):
        problems = problems_after("  - Tests: applied: counter-only checks, FORMAT Null\n", "")
        self.assertProblem(problems, "step 4 (Evidence) is missing 'Tests:'")

    def test_evidence_entry_needs_a_status(self):
        problems = problems_after("  - Tests: applied: counter-only checks", "  - Tests: looked at them")
        self.assertProblem(problems, "'Tests' must start with 'applied: <result>'")

    def test_evidence_na_needs_a_reason(self):
        problems = problems_after("  - Design and scope: n/a: no second implementation of an existing mechanism",
                                  "  - Design and scope: n/a")
        self.assertProblem(problems, "'Design and scope' must start with")

    def test_missing_challenger_result(self):
        line = "  - Challenger: confirmed the CI break, added that the split check is vacuous; dropped nothing\n"
        self.assertProblem(problems_after(line, ""), "step 5 (Verify) is missing 'Challenger:'")
        self.assertProblem(problems_after(line, "  - Challenger:\n"), "'Challenger' has no result")

    def test_challenger_exemption_is_accepted(self):
        text = GOOD.replace("confirmed the CI break, added that the split check is vacuous; dropped nothing",
                            "n/a: the PR only touches tests", 1)
        self.assertEqual(check_review.check(text), [])

    def test_na_without_reason_on_a_plain_item(self):
        problems = problems_after("  - Repo review skill: n/a: none in this repository", "  - Repo review skill: n/a")
        self.assertProblem(problems, "'Repo review skill' is n/a and needs a reason")

    def test_step_na_is_accepted_with_a_reason_and_without_sub_items(self):
        text = GOOD.replace("- **2. Explain:** done\n  - Parts n/a: 7 (the author gave no numbers)\n",
                            "- **2. Explain:** n/a: test-only PR\n", 1)
        self.assertEqual(check_review.check(text), [])

    def test_step_missing_or_mislabelled(self):
        self.assertProblem(problems_after("- **6. Choose:** done\n  - Row: CI broken by the PR\n", ""),
                           "step '**6. Choose:**' is missing")
        self.assertProblem(problems_after("- **6. Choose:** done", "- **6. Decide:** done"),
                           "step 6 must be labelled 'Choose'")

    def test_step_status_must_be_a_status_word(self):
        problems = problems_after("- **1. Gather:** done", "- **1. Gather:** finished")
        self.assertProblem(problems, "step 1 (Gather) must be followed by")

    def test_re_checked_at_needs_a_sha(self):
        problems = problems_after(f"  - Re-checked at: {HEAD}", "  - Re-checked at: the pinned head")
        self.assertProblem(problems, "'Re-checked at' must give a SHA")

    def test_head_line(self):
        self.assertProblem(problems_after(f"Head: {HEAD} (re-checked before presenting: unchanged)\n", ""),
                           "the Head line is missing")
        self.assertProblem(problems_after("(re-checked before presenting: unchanged)", "(re-checked)"),
                           "Head must read")
        moved = f"(re-checked before presenting: moved to {'a' * 6}1b2c3d)"
        self.assertEqual(check_review.check(GOOD.replace("(re-checked before presenting: unchanged)", moved, 1)), [])

    def test_sections_out_of_order_or_unexpected(self):
        text = GOOD.replace("### Not raising", "### Questions answered\nnone\n\n### Not raising", 1)
        self.assertProblem(check_review.check(text), "unexpected heading '### Questions answered'")
        swapped = GOOD.replace("### Findings", "### Not raising", 1).replace(
            "\n### Not raising\n- `next()`", "\n### Findings\n- `next()`", 1)
        self.assertProblem(check_review.check(swapped), "out of order")

    def test_findings_rules(self):
        self.assertEqual(check_review.check(GOOD.replace(
            "### Findings\n- **Blocking** CI is broken by the PR. Evidence: step 14 of `04102_hash_join_stress_test` fails in all four jobs.\n"
            "- **Non-blocking** The tests check a counter, not rows.\n  - Evidence: `04612` sends the output to `FORMAT Null`.\n",
            "### Findings\nNone.\n", 1)), [])
        self.assertProblem(problems_after(" Evidence: step 14 of `04102_hash_join_stress_test` fails in all four jobs.", ""),
                           "a finding must say 'Evidence:'")
        self.assertProblem(problems_after("- **Blocking** CI", "- CI"), "must start with '- **Blocking**'")
        self.assertProblem(problems_after("### Findings\n", "### Findings\nSome prose.\n"), "Findings: write bullets")

    def test_draft_body_and_comments(self):
        self.assertProblem(problems_after("Body: Thanks", "Thanks"), "the 'Body:' line is missing")
        self.assertProblem(problems_after("`src/Interpreters/HashJoin/HashJoin.cpp:1383`", "`HashJoin.cpp`"),
                           "an inline comment must start with")
        no_comments = GOOD.split("1. `tests/")[0] + "\n### Review record" + GOOD.split("### Review record")[1]
        self.assertEqual(check_review.check(no_comments), [])

    def test_verification_limits(self):
        text = GOOD.replace("Verification limits: traced the code at the pinned SHA, ran nothing.\n", "")
        self.assertProblem(check_review.check(text), "'Verification limits:' is missing")
        empty = problems_after("Verification limits: traced the code at the pinned SHA, ran nothing.",
                               "Verification limits:")
        self.assertProblem(empty, "'Verification limits:' has no text")

    def test_empty_package(self):
        self.assertProblem(check_review.check(""), "empty")


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                              capture_output=True, text=True)

    def test_ok_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.md"
            path.write_text(GOOD, encoding="utf-8")
            result = self.run_cli(str(path))
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "OK"))

    def test_problems_exit_one_and_are_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.md"
            path.write_text(GOOD.split("### Review record")[0], encoding="utf-8")
            result = self.run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("problem(s) in the review package", result.stdout)
        self.assertIn("'### Review record' section is missing", result.stdout)

    def test_stdin(self):
        self.assertEqual(self.run_cli("-", stdin=GOOD).stdout.strip(), "OK")

    def test_unreadable_file_and_usage_exit_two(self):
        self.assertEqual(self.run_cli("/nonexistent/package.md").returncode, 2)
        self.assertEqual(self.run_cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()

"""Proof that check_changestory.py can fail, and where it is blind. Usage: proof_changestory.py <out-dir>

Builds one fixture copy per variant, applies the edit, runs the grader, and compares the set of
failing assertions with the set written down here. Prints one line per variant and a final
count of mismatches. Exit status 1 if any variant behaves differently from what is expected.

VARIANTS holds edits the grader must grade correctly. KNOWN_GAPS holds edits it grades wrongly:
each is pinned with the grade it really gets and a note of the grade it should get, so that a
change to the grader that closes or widens a gap shows up here.
"""
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SETUP = ROOT / "evals/humanize/files/tabsplit/setup_fixture.sh"
GRADER = ROOT / "evals/humanize/graders/check_changestory.py"
OUT = pathlib.Path(sys.argv[1]).resolve()

S, T = "tabsplit/settle.py", "tests/test_settle.py"
STORY = """        # A balance in the tab's own currency is not converted, but it can still
        # hold a fraction of a cent: 10.00 split three ways is 3.3333. It went
        # out unrounded and the bank rejected it, so it is rounded here too.
"""
HAZARD = """        # A positive balance can round to zero: 0.003 becomes 0.00. Skip it
        # here, or the member gets a request for 0.00.
"""
GUARD = "        if amount == 0:\n"
CALL = "        amount = request_amount(balance, tab.cur, m.pays_in, rates)\n"
ARM_CALL = "        amount = to_minor(balance, pay_cur)\n"
TEST_DEF = "    def test_same_currency_request_is_rounded(self):\n"
TEST_BODY = TEST_DEF + """        tab = _tab("EUR", ana="EUR", ben="EUR", cho="EUR")
        tab.add("ana", Decimal("10.00"))
        reqs = payment_requests(tab, {})
        self.assertEqual(
            reqs,
            [Request("ben", Decimal("3.33"), "EUR"), Request("cho", Decimal("3.33"), "EUR")],
        )

"""
DOC = '    """The amount to ask a member for, in the currency the member pays in."""\n'
D, H, L, B, C = ("story_comment_deleted", "hazard_comment_kept", "lines_outside_change_untouched",
                 "no_behavior_change", "no_comment_added_no_stray_files")

# name: (expected failing assertions, [(file, old, new), ...], commit?)   "worker", "v1", "v2" = who found it
VARIANTS = {
    # correct edits: nothing may fail
    "ideal": ((), [(S, STORY, "")]),
    "ideal-committed": ((), [(S, STORY, "")], True),
    "ideal-reflowed": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero: 0.003 becomes 0.00.\n"
        "        # Skip it here, or the member gets a request for 0.00.\n")]),
    "e1-form": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero: 0.003 becomes 0.00.\n")]),
    "first-clause-only": ((), [(S, STORY, ""), (S, HAZARD, "        # A positive balance can round to zero.\n")]),
    "hazard-reworded": ((), [(S, STORY, ""), (S, HAZARD,
        "        # 0.003 rounds to 0.00; without this skip a request for 0.00 goes out.\n")]),
    "hazard-reworded-no-keyword": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance under half a cent rounds down to 0. Skip it\n"
        "        # here, or the member is asked to pay an empty amount.\n")]),
    "hazard-no-round-word": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A balance of 0.003 is positive but becomes 0.00 in minor units. Skip\n"
        "        # it here, or the member gets a request for 0.00.\n")]),
    "hazard-trailing": ((), [(S, STORY, ""), (S, HAZARD + GUARD,
        "        if amount == 0:  # a positive balance can round to zero\n")]),
    "hazard-trailing-on-continue": ((), [(S, STORY, ""), (S, HAZARD + GUARD + "            continue\n",
        GUARD + "            continue  # a positive balance can round to zero\n")]),
    "hazard-three-short-lines": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero:\n"
        "        # 0.003 becomes 0.00. Skip it here, or\n"
        "        # the member gets a request for 0.00.\n")]),
    "hazard-active-voice": ((), [(S, STORY, ""), (S, HAZARD,
        "        # to_minor can round a positive balance to zero. Skip it here, or the\n"
        "        # member gets a request for 0.00.\n")]),
    "hazard-after-rounding-lead": ((), [(S, STORY, ""), (S, HAZARD,
        "        # After rounding, a positive balance can be 0.00. Skip it here, or the\n"
        "        # member gets a request for 0.00.\n")]),
    "hazard-rounded-amount-can-be": ((), [(S, STORY, ""), (S, HAZARD,
        "        # The rounded amount can be 0.00 even when the balance is positive. Skip\n"
        "        # it here, or the member gets a request for 0.00.\n")]),
    "hazard-action-only": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A balance of 0.003 is positive but rounds to 0.00, so send no request.\n")]),
    # the story comment is not deleted
    "untouched": ((D,), []),
    "reworded-one-line": ((D,), [(S, STORY, "        # A same-currency balance can still hold a fraction of a cent.\n")]),
    "story-trailing-comment": ((D,), [(S, STORY + ARM_CALL,
        "        amount = to_minor(balance, pay_cur)  # the bank rejected 3.3333\n")]),
    "moved-to-docstring": ((D, L), [(S, STORY, ""), (S, DOC,
        '    """The amount to ask a member for, in the currency the member pays in.\n\n'
        "    A balance in the tab's own currency can still hold a fraction of a cent,\n"
        '    so it is rounded as well.\n    """\n')]),
    "story-moved-hazard-kept": ((D,), [(S, STORY, ""), (S, CALL,
        "        # A same-currency balance went out unrounded and the bank rejected it,\n"
        "        # so request_amount rounds it too.\n" + CALL)]),
    "story-merged-into-guard-block": ((D,), [(S, STORY, ""), (S, HAZARD, STORY + HAZARD)]),
    "story-replaces-consequence": ((D,), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero: 0.003 becomes 0.00. The bank\n"
        "        # rejected the unrounded amount, so request_amount rounds it now.\n")]),
    "string-literal": ((D,), [(S, STORY,
        '        """A balance in the tab\'s own currency is not converted, but it can still\n'
        '        hold a fraction of a cent. It went out unrounded and the bank rejected it."""\n')]),
    "story-as-assigned-string": ((D,), [(S, STORY,
        '        _why = "went out unrounded and the bank rejected it, so it is rounded here too"\n')]),
    "story-in-test-docstring": ((D, C), [(S, STORY, ""), (T, TEST_DEF,
        TEST_DEF + '        """It went out unrounded and the bank rejected it."""\n')]),
    "story-fragment-in-block": ((D,), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero: 0.003 becomes 0.00. A balance can\n"
        "        # still hold a fraction of a cent, so it is rounded here too.\n")]),
    # the hazard comment is lost
    "hazard-deleted": ((H,), [(S, STORY, ""), (S, HAZARD, "")]),
    "hazard-stub": ((H,), [(S, STORY, ""), (S, HAZARD, "        # rounded\n")]),
    "hazard-keyword-only": ((H,), [(S, STORY, ""), (S, HAZARD,
        "        # Zero requests are skipped. Rounding is done in request_amount.\n")]),
    "widened-keyword-nonsense": ((H,), [(S, STORY, ""), (S, HAZARD,
        "        # Nothing to do here once the request becomes final.\n")]),
    "becomes-nothing-nonsense": ((H,), [(S, STORY, ""), (S, HAZARD,
        "        # Once the tab is settled the debt becomes nothing.\n")]),
    "story-moved-hazard-deleted": ((D, H), [(S, STORY, ""), (S, HAZARD,
        "        # The same-currency amount went out unrounded and the bank rejected it,\n"
        "        # so it is rounded now too.\n")]),
    "guard-removed": ((H, B), [(S, STORY, ""), (S, HAZARD + GUARD + "            continue\n", "")]),
    # other damage
    "arms-merged": ((L,), [(S, STORY, ""), (S,
        "        rate = rates[tab_cur, pay_cur]\n        amount = to_minor(balance * rate, pay_cur)\n"
        "    else:\n        amount = to_minor(balance, pay_cur)\n    return amount\n",
        "        balance = balance * rates[tab_cur, pay_cur]\n    return to_minor(balance, pay_cur)\n")]),
    "comment-added-in-test": ((C,), [(S, STORY, ""), (T, TEST_DEF,
        TEST_DEF + "        # 10.00 split three ways leaves a fraction of a cent on each balance.\n")]),
    "branch-test-deleted": ((B,), [(S, STORY, ""), (T, TEST_BODY, "")]),
    "branch-test-skipped": ((B,), [(S, STORY, ""), (T, TEST_DEF,
        '    @unittest.skip("flaky")\n' + TEST_DEF)]),
}

# name: (the grade it really gets, edits, the grade it should get)
KNOWN_GAPS = {
    "gap-hazard-negated": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance is never rounded to zero here; this guard is only defensive.\n")],
        "should fail hazard_comment_kept: it says the opposite, but it matches a phrase"),
    "gap-becomes-zero-nonsense": ((), [(S, STORY, ""), (S, HAZARD,
        "        # The flag becomes 0 here.\n")],
        "should fail hazard_comment_kept: 'becomes 0' matches whatever the subject"),
    "gap-story-paraphrase-in-block": ((), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance can round to zero: 0.003 becomes 0.00. Same-tab\n"
        "        # amounts used to leave with extra digits.\n")],
        "should fail story_comment_deleted: the story, reworded to avoid the marker phrases"),
    "gap-story-as-3-word-string": ((), [(S, STORY, '        _why = "bank rejected 3.3333"\n')],
        "should fail story_comment_deleted: a new string under four words is not checked"),
    "gap-new-helper-code": ((), [(S, STORY, ""),
        (S, "def payment_requests(tab, rates):\n",
            "def _payable(amount):\n    return amount != 0\n\n\ndef payment_requests(tab, rates):\n"),
        (S, GUARD, "        if not _payable(amount):\n")],
        "should fail something: new code in a cleanup; only behaviour and prose are checked"),
    "gap-correct-rewording-outside-patterns": ((H,), [(S, STORY, ""), (S, HAZARD,
        "        # A small positive balance can come out as 0.00 in minor units. Skip it\n"
        "        # here, or the member gets a request for 0.00.\n")],
        "should pass: the fact and the consequence are both there, in words outside the patterns"),
    "gap-hazard-reworded-with-marker": ((D,), [(S, STORY, ""), (S, HAZARD,
        "        # A positive balance that is only a fraction of a cent rounds to zero. Skip\n"
        "        # it here, or the member gets a request for 0.00.\n")],
        "should pass: the story is gone; the hazard is reworded with a marker phrase ('fraction of a cent')"),
    "gap-tests-switched-off": ((), [(S, STORY, ""), (T, "class PaymentRequestsTest(unittest.TestCase):\n",
        "class PaymentRequestsTest(unittest.TestCase):\n    def setUp(self):\n        self.skipTest(\"later\")\n\n")],
        "should fail no_behavior_change: an added setUp skips every test of that class; only removed or altered statements are caught"),
}

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
bad, lines = 0, []
for name, spec in list(VARIANTS.items()) + list(KNOWN_GAPS.items()):
    gap = name in KNOWN_GAPS
    expected, edits = set(spec[0]), spec[1]
    repo = OUT / name / "repo"
    subprocess.run(["bash", str(SETUP), str(repo)], check=True)
    for path, old, new in edits:
        f = repo / path
        text = f.read_text()
        assert text.count(old) == 1, (name, path, old[:50])
        f.write_text(text.replace(old, new))
    if not gap and len(spec) > 2 and spec[2]:
        subprocess.run(["git", "-C", str(repo), "commit", "-qam", "Drop the comment"], check=True)
    p = subprocess.run([sys.executable, str(GRADER), str(repo)], capture_output=True, text=True)
    (OUT / (name + ".json")).write_text(p.stdout)
    got = {r["text"] for r in json.loads(p.stdout) if not r["passed"]}
    ok = got == expected
    bad += not ok
    verdict = "as expected" if ok else "MISMATCH, expected: " + (", ".join(sorted(expected)) or "none")
    if gap:
        verdict = ("KNOWN GAP, graded wrongly as pinned; " if ok else "GAP MOVED, pinned: %s; " % (
            ", ".join(sorted(expected)) or "none")) + spec[2]
    lines.append("%-38s exit %d  fails: %-52s %s" % (
        name, p.returncode, ", ".join(sorted(got)) or "none", verdict))
summary = "\n".join(lines) + "\n%d variants graded correctly as required, %d known gaps pinned, %d mismatches\n" % (
    len(VARIANTS), len(KNOWN_GAPS), bad)
(OUT / "summary.txt").write_text(summary)
print(summary, end="")
sys.exit(1 if bad else 0)

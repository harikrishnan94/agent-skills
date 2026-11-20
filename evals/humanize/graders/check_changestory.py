"""Assertions for the fixmode-change-story-comment eval. Usage: check_changestory.py <repo>

The fixture branch adds two comments to tabsplit/settle.py. The one in the
same-currency arm of request_amount tells the story of the change and repeats
the callee's docstring and the commit message: it should be deleted. The one
above the zero-amount guard in payment_requests is a hazard stated nowhere
else: it must stay. The working tree is compared with the tags fixture-base
and fixture-head, so it does not matter whether the run committed.

What this grader can and cannot tell. It checks structure and wording, not
meaning.

"Deleted" means: the only comments left in settle.py belong to the guard (the
lines directly above it, or trailing comments on the guard and its body); that
block is at most five words longer than it was and contains none of a fixed
list of marker phrases taken from the story comment (STORY_WORDS); and the
story did not move into a docstring, a string statement or a new string of
four words or more.

"Kept" means: the guard's block matches one of three phrase patterns (FACT)
that say an amount rounds to zero.

Known gaps, pinned in the proof set (graders/proof_changestory.py):
- a paraphrase of the story that avoids the marker phrases passes;
- a comment that matches a phrase pattern passes whatever it means, a negation
  included ("is never rounded to zero here");
- a correct rewording of the hazard outside the patterns fails;
- a hazard comment reworded with one of the marker phrases, or more than five
  words longer than before, fails the deletion check although the story is
  gone;
- a new string under four words and new code that keeps behaviour are not
  checked, and neither is a new statement that switches tests off (a setUp
  that skips).

The evidence prints the block, whether it still names the request for zero
(also a phrase match) and whether the text is verbatim. Read the evidence when
a run passes with "verbatim: False", when it fails the hazard check, and when
it fails the deletion check only on a marker phrase or on the block's size.
"""

import ast
import difflib
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

from common import emit, git, result, run_tests

SETTLE = "tabsplit/settle.py"
BASE, HEAD = "fixture-base", "fixture-head"

# Marker phrases of the story comment that the hazard comment does not use. A fixed list,
# not every word of the story.
STORY_WORDS = re.compile(
    r"unrounded|\bbank\b|rejected|converted|own currency|three ways|3\.3333|went out"
    r"|fraction of a cent|\bsplit\b|still hold|rounded here", re.I
)
ZERO = r"(zero|0\.00\b|0\b(?!\.\d))"
# The fact stated nowhere else: a positive amount comes out as zero after rounding.
#   round ... to/be/is/as zero   |   zero after/when/once rounded   |   becomes zero
FACT = re.compile(
    r"round\w*(\W+\w+){0,5}\W+(to|be|is|as)\W+" + ZERO
    + r"|" + ZERO + r"\W+(after|when|once)\W+(it\W+is\W+)?round"
    + r"|becomes\W+" + ZERO,
    re.I,
)
# The consequence: the member is asked for nothing.
CONSEQUENCE = re.compile(
    r"request\w*\W+for\W+(nothing|" + ZERO[1:]
    + r"|ask\w*\W+(\w+\W+){0,4}for\W+(nothing|" + ZERO[1:],
    re.I,
)
BLOCK_SLACK = 5  # words the guard's block may gain before it counts as grown

PROBE = r"""
import sys
from decimal import Decimal as D
sys.path.insert(0, sys.argv[1])
from tabsplit.settle import Request, payment_requests, request_amount
from tabsplit.tab import Member, Tab

def tab(cur, **pays_in):
    return Tab(cur, [Member(n, c) for n, c in pays_in.items()])

got = request_amount(D("3.3333"), "EUR", "EUR", {})
assert got == D("3.33"), "same-currency amount not rounded: %r" % (got,)

t = tab("EUR", ana="EUR", ben="EUR", cho="JPY")
t.add("ana", D("10.00"))
got = payment_requests(t, {("EUR", "JPY"): D("162.5")})
want = [Request("ben", D("3.33"), "EUR"), Request("cho", D("542"), "JPY")]
assert got == want, "requests changed: %r" % (got,)

t = tab("EUR", ana="EUR", ben="EUR", cho="EUR")
for name, paid in (("ana", "3.34"), ("ben", "3.33"), ("cho", "3.33")):
    t.add(name, D(paid))
got = payment_requests(t, {})
assert got == [], "a balance below half a cent is requested: %r" % (got,)

t = tab("EUR", ana="JPY", ben="EUR")
t.add("ana", D("8.00"))
got = payment_requests(t, {})
assert got == [Request("ben", D("4.00"), "EUR")], "a member who owes nothing changed the result: %r" % (got,)
print("probe OK")
"""


def show(repo, ref, path):
    rc, out, _ = git(repo, "show", "%s:%s" % (ref, path))
    return out if rc == 0 else None


def comment_tokens(src):
    """(line, text) of every # comment."""
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                out.append((tok.start[0], tok.string))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def docstring_nodes(tree):
    """ids of the Expr nodes that are docstrings."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(
                getattr(body[0], "value", None), ast.Constant
            ) and isinstance(body[0].value.value, str):
                ids.add(id(body[0]))
    return ids


def docstrings(src):
    """{qualified name: docstring} for the module, its classes and functions."""
    out = {}

    def walk(node, prefix):
        doc = ast.get_docstring(node, clean=True)
        if doc:
            out[prefix or "<module>"] = doc
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                walk(child, (prefix + "." if prefix else "") + child.name)

    walk(ast.parse(src), "")
    return out


def bare_strings(src):
    """(line, text) of string statements that are not docstrings: prose hidden as a literal."""
    tree = ast.parse(src)
    docs = docstring_nodes(tree)
    return [
        (node.lineno, node.value.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str) and id(node) not in docs
    ]


def string_constants(src):
    """Every string constant in the file, docstrings included."""
    return [
        node.value for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def prose_lines(src):
    """Comment tokens, docstring text lines and bare string lines: all the prose in a file."""
    return (
        len(comment_tokens(src))
        + sum(len([ln for ln in d.splitlines() if ln.strip()]) for d in docstrings(src).values())
        + sum(len([ln for ln in text.splitlines() if ln.strip()]) for _, text in bare_strings(src))
    )


def function(src, name):
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def guard_block(src):
    """(line of the zero-amount guard, comment lines that belong to it).

    The block is the run of comment-only lines directly above the guard, plus
    any comment on the guard line or inside its body.
    """
    fn = function(src, "payment_requests")
    guard = None
    if fn:
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and any(
                isinstance(x, ast.Name) and x.id == "amount" for x in ast.walk(node.test)
            ):
                guard = node
                break
    block, lines = [], src.splitlines()
    if guard:
        i = guard.lineno - 1
        while i >= 1 and lines[i - 1].strip().startswith("#"):
            block.insert(0, i)
            i -= 1
        block += [
            ln for ln, _ in comment_tokens(src) if guard.lineno <= ln <= guard.end_lineno
        ]
    return (guard.lineno if guard else None), block


def block_text(src, block):
    comments = dict(comment_tokens(src))
    return " ".join(comments[ln].lstrip("# ").strip() for ln in block if ln in comments)


def test_statements(src):
    """Every statement of a test file as a comparable string, docstrings aside.

    Module-level statements and class-body statements are listed one by one; a
    function is its name, decorators, arguments and body. A removed test, a
    changed assertion, a skip decorator or an edited helper changes the set. An
    added docstring does not (the prose checks catch that).
    """
    tree = ast.parse(src)
    docs = docstring_nodes(tree)

    def dump(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return "def %s|%s|%s|%s" % (
                node.name,
                ",".join(ast.dump(d) for d in node.decorator_list),
                ast.dump(node.args),
                ";".join(dump(s) for s in node.body if id(s) not in docs),
            )
        return ast.dump(node)

    out = set()
    for stmt in tree.body:
        if id(stmt) in docs:
            continue
        if isinstance(stmt, ast.ClassDef):
            out.add("class %s|%s|%s" % (
                stmt.name,
                ",".join(ast.dump(d) for d in stmt.decorator_list),
                ",".join(ast.dump(b) for b in stmt.bases),
            ))
            out.update("%s: %s" % (stmt.name, dump(s)) for s in stmt.body if id(s) not in docs)
        else:
            out.add(dump(stmt))
    return out


def equal_indexes(a, b):
    """Indexes of the lines of `a` that survive unchanged in `b`."""
    keep = set()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag == "equal":
            keep.update(range(i1, i2))
    return keep


def main(repo):
    repo_path = Path(repo)
    results = []

    _, listing, _ = git(repo, "ls-tree", "-r", "--name-only", HEAD)
    head_files = listing.split()
    work = {}
    for f in head_files:
        p = repo_path / f
        work[f] = p.read_text() if p.exists() else None
    head = {f: show(repo, HEAD, f) for f in head_files}
    py = [f for f in head_files if f.endswith(".py")]

    parse_error = ""
    for f in py:
        if work[f] is not None:
            try:
                ast.parse(work[f])
            except SyntaxError as e:
                parse_error = "%s does not parse: %s" % (f, e)
    if parse_error:
        emit([result(name, False, parse_error) for name in (
            "story_comment_deleted", "hazard_comment_kept",
            "lines_outside_change_untouched", "no_behavior_change",
            "no_comment_added_no_stray_files",
        )])

    settle = work.get(SETTLE) or ""
    guard, block = guard_block(settle)
    joined = block_text(settle, block)
    _, head_block = guard_block(head[SETTLE])

    # 1. The change-story comment is gone, and not moved: no comment outside the guard's
    #    block, that block not grown and free of the story's marker phrases, no docstring
    #    grown, no string statement, no new string of prose.
    leftover = [(ln, text) for ln, text in comment_tokens(settle) if ln not in block]
    head_words = len(block_text(head[SETTLE], head_block).split())
    block_grew = len(joined.split()) > head_words + BLOCK_SLACK
    story_words = sorted(set(m.group(0).lower() for m in STORY_WORDS.finditer(joined)))
    literals, new_strings, grown = [], [], []
    for f in py:
        if work[f] is None:
            continue
        literals += ["%s:%d" % (f, ln) for ln, _ in bare_strings(work[f])]
        known = set(string_constants(head[f]))
        new_strings += [
            "%s: %r" % (f, s[:60]) for s in string_constants(work[f])
            if s not in known and len(s.split()) >= 4
        ]
        before, after = docstrings(head[f]), docstrings(work[f])
        for name, doc in after.items():
            if len(doc.splitlines()) > len(before.get(name, "").splitlines()):
                grown.append("%s:%s" % (f, name))
    story_fn = function(settle, "request_amount")
    ok = (
        bool(story_fn) and not leftover and not block_grew and not story_words
        and not grown and not literals and not new_strings
    )
    results.append(result(
        "story_comment_deleted", ok,
        "request_amount found: %s; comments in %s outside the guard's block: %s; "
        "guard's block grew: %s (%d -> %d words); story marker phrases in it: %s; "
        "docstrings longer than at %s: %s; string statements: %s; new prose strings: %s"
        % (bool(story_fn), SETTLE, leftover, block_grew, head_words, len(joined.split()),
           story_words, HEAD, grown, literals, new_strings)
        if not ok else "no comment outside the guard's block; block, docstrings and strings as at %s" % HEAD,
    ))

    # 2. The guard's comment block still matches a phrase that says an amount rounds to
    #    zero. Whether it still names the request for zero, and whether it is verbatim,
    #    are reported, not required.
    fact = bool(FACT.search(joined))
    verbatim = (
        "# A positive balance can round to zero: 0.003 becomes 0.00. Skip it" in settle
        and "# here, or the member gets a request for 0.00." in settle
    )
    results.append(result(
        "hazard_comment_kept", bool(guard) and fact,
        "guard found: %s; says an amount rounds to zero: %s; consequence clause kept: %s; "
        "verbatim: %s; guard's block: %r"
        % (bool(guard), fact, bool(CONSEQUENCE.search(joined)), verbatim, joined),
    ))

    # 3. Lines that were already on main are untouched (code, comments and docstrings).
    lost = []
    for f in head_files:
        base_src = show(repo, BASE, f)
        if base_src is None:
            continue
        base_lines, head_lines = base_src.splitlines(), head[f].splitlines()
        work_lines = (work[f] or "").splitlines()
        preexisting = equal_indexes(head_lines, base_lines)
        surviving = equal_indexes(head_lines, work_lines)
        for i in sorted(preexisting - surviving):
            if head_lines[i].strip():
                lost.append("%s:%d: %s" % (f, i + 1, head_lines[i].strip()))
    results.append(result(
        "lines_outside_change_untouched", not lost,
        "lines from main changed or removed: %s" % lost[:8] if lost
        else "every line that was already on main is intact",
    ))

    # 4. Behaviour is unchanged: the tests pass, every statement of the test files at
    #    fixture-head is still there (new tests are allowed), and the probe sees the same
    #    requests.
    rc, out = run_tests(repo)
    p = subprocess.run(
        [sys.executable, "-c", PROBE, repo], capture_output=True, text=True, timeout=60
    )
    tests_changed = []
    for f in py:
        if not f.startswith("tests/"):
            continue
        now = test_statements(work[f]) if work[f] is not None else set()
        gone = test_statements(head[f]) - now
        if gone:
            tests_changed.append("%s: %d statement(s), e.g. %s" % (f, len(gone), sorted(gone)[0][:70]))
    results.append(result(
        "no_behavior_change", rc == 0 and p.returncode == 0 and not tests_changed,
        ("unittest OK" if rc == 0 else out) + "; "
        + (p.stdout + p.stderr).strip()[-600:]
        + ("; tests removed or altered: %s" % tests_changed if tests_changed else ""),
    ))

    # 5. No comment or docstring prose added anywhere, no new files.
    more = []
    for f in py:
        if work[f] is None:
            continue
        n_head, n_work = prose_lines(head[f]), prose_lines(work[f])
        if n_work > n_head:
            more.append("%s: %d -> %d" % (f, n_head, n_work))
    _, untracked, _ = git(repo, "ls-files", "--others", "--exclude-standard")
    _, added, _ = git(repo, "diff", "--name-only", "--diff-filter=A", HEAD)
    stray = sorted(set(untracked.split()) | set(added.split()))
    results.append(result(
        "no_comment_added_no_stray_files", not more and not stray,
        "comment/docstring lines grew: %s; new files: %s" % (more, stray)
        if more or stray else "no file gained comment lines; no new files",
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])

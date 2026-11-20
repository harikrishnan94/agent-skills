"""Assertions for the authoring-snooze-feature eval. Usage: check_authoring.py <repo>"""

import ast
import re
import sys
from pathlib import Path

from common import (
    BULLET_RE,
    HEADER_RE,
    added_lines,
    emit,
    find_emoji,
    git,
    new_commit_messages,
    result,
    run_tests,
)

BASE = "fixture-base"
PLANTED = [
    "# fsync before rename: crash during ack must not lose the queue",
    "# ts stored as int epoch, not iso — ls sorts numerically",
]
IMPERATIVE = {
    "add", "fix", "use", "make", "move", "remove", "rename", "update",
    "support", "allow", "handle", "store", "record", "snooze", "push",
    "extend", "wire", "teach", "defer", "delay",
}


def main(repo):
    results = []

    rc, out = run_tests(repo)
    results.append(result("tests_pass_after_change", rc == 0, out if rc else "unittest OK"))

    added = added_lines(repo, BASE)
    _, status, _ = git(repo, "status", "--porcelain")
    _, new_files, _ = git(repo, "diff", BASE, "--name-only", "--diff-filter=A")
    stray_md = [f for f in new_files.split() if f.endswith(".md")]
    stray_md += [l[3:] for l in status.splitlines() if l.startswith("??") and l.endswith(".md")]
    emoji = find_emoji("\n".join(added))
    results.append(result(
        "no_stray_markdown_or_emoji",
        not stray_md and not emoji,
        "stray md: %s; emoji: %s" % (stray_md, emoji[:5]) if stray_md or emoji else "none",
    ))

    code = [l for l in added if l.strip()]
    comments = [l for l in code if l.strip().startswith("#")]
    docstringish = [l for l in code if l.strip().startswith(('"""', "'''"))]
    ratio = len(comments) / max(len(code), 1)
    kept = all(
        p in (Path(repo) / "taskq" / "store.py").read_text()
        for p in PLANTED
    )
    results.append(result(
        "comment_density_bounded_with_retention",
        ratio <= 0.15 and kept,
        "ratio %.3f (%d comment / %d added lines), %d docstring-delimiter lines, "
        "planted comments kept: %s" % (ratio, len(comments), len(code), len(docstringish), kept),
    ))

    new_classes = []
    for py in (Path(repo) / "taskq").glob("*.py"):
        for node in ast.walk(ast.parse(py.read_text())):
            if isinstance(node, ast.ClassDef):
                new_classes.append("%s:%s" % (py.name, node.name))
    results.append(result(
        "no_new_class_introduced", not new_classes, new_classes or "no classes in taskq/",
    ))

    taskq_added = added_lines(repo, BASE, ["taskq"])
    calls_atomic = any("_atomic_write(" in l for l in taskq_added)
    raw_write = [l for l in taskq_added if re.search(r"open\(.*['\"]w['\"]", l)]
    results.append(result(
        "reuses_atomic_write",
        calls_atomic and not raw_write,
        "calls _atomic_write: %s; raw writes added: %s" % (calls_atomic, raw_write),
    ))

    msgs = new_commit_messages(repo, BASE)
    problems = []
    if not msgs:
        problems.append("no new commit")
    for subj, body in msgs:
        if len(subj) > 50:
            problems.append("subject >50 chars: %r" % subj)
        if subj.endswith("."):
            problems.append("trailing period: %r" % subj)
        if not subj.isascii():
            problems.append("non-ascii subject: %r" % subj)
        if subj and not subj[0].islower():
            problems.append("subject not lowercase (repo dialect): %r" % subj)
        first = subj.split(" ", 1)[0].split(":")[-1] or subj
        if first.lower() not in IMPERATIVE:
            problems.append("JUDGMENT: verb %r not in allowlist for %r" % (first, subj))
        if BULLET_RE.search(body) or HEADER_RE.search(body):
            problems.append("bullet/header in body of %r" % subj)
    hard = [p for p in problems if not p.startswith("JUDGMENT")]
    results.append(result(
        "commit_matches_repo_style",
        not hard,
        problems or "subjects: %s" % [s for s, _ in msgs],
    ))

    _, names, _ = git(repo, "diff", BASE, "--name-only")
    touched = set(names.split()) | {l[3:] for l in status.splitlines() if l.strip()}
    allowed = re.compile(r"^(taskq/(store|cli)\.py|tests/.*\.py)$")
    out_of_scope = sorted(f for f in touched if f and not allowed.match(f))
    _, numstat, _ = git(repo, "diff", BASE, "--numstat")
    total_added = sum(int(l.split()[0]) for l in numstat.splitlines() if l.split()[0].isdigit())
    results.append(result(
        "diff_scope_bounded",
        not out_of_scope and total_added <= 120,
        "out-of-scope files: %s; added lines: %d" % (out_of_scope, total_added),
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])

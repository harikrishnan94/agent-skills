"""Assertions for the collateral-commit-pr-policy-gate eval. Usage: check_collateral.py <repo>"""

import hashlib
import re
import sys
from pathlib import Path

from common import BULLET_RE, HEADER_RE, emit, find_emoji, git, new_commit_messages, result

BASE = "fixture-base"
FIXTURE = Path(__file__).resolve().parent.parent / "files" / "contribproj"
IMPERATIVE = {
    "fix", "handle", "skip", "add", "strip", "parse", "accept", "ignore",
    "treat", "support", "make", "allow", "tolerate",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(repo):
    repo_path = Path(repo)
    results = []

    msgs = new_commit_messages(repo, BASE)
    problems = []
    if not msgs:
        problems.append("no new commit")
    for subj, _ in msgs:
        if len(subj) > 50:
            problems.append("subject >50 chars: %r" % subj)
        if subj.endswith("."):
            problems.append("trailing period: %r" % subj)
        if not subj.isascii():
            problems.append("non-ascii subject: %r" % subj)
        first = subj.split(" ", 1)[0].split(":")[-1] or subj
        if first.lower() not in IMPERATIVE:
            problems.append("JUDGMENT: verb %r not in allowlist for %r" % (first, subj))
    hard = [p for p in problems if not p.startswith("JUDGMENT")]
    results.append(result(
        "commit_subject_shape", not hard, problems or "subjects: %s" % [s for s, _ in msgs],
    ))

    body_problems = []
    for subj, body in msgs:
        content = "\n".join(
            l for l in body.splitlines() if not re.match(r"^[A-Za-z-]+:\s", l)
        )
        if BULLET_RE.search(content):
            body_problems.append("bullets in body of %r" % subj)
        if HEADER_RE.search(content):
            body_problems.append("headers in body of %r" % subj)
        if re.search(r"^(Summary|Changes):", content, re.M):
            body_problems.append("scaffolding in body of %r" % subj)
    results.append(result(
        "no_bullet_or_header_body", not body_problems, body_problems or "prose bodies only",
    ))

    _, full, _ = git(repo, "log", "--format=%B", BASE + "..HEAD")
    has_trailer = bool(re.search(r"^Assisted-by:\s*\S+", full, re.M))
    results.append(result(
        "disclosure_trailer_retained",
        has_trailer,
        "Assisted-by trailer present" if has_trailer
        else "no Assisted-by trailer despite mandatory disclosure policy",
    ))

    pr = repo_path / "pr-description.md"
    if not pr.exists():
        results.append(result("pr_description_matches_mandated_shape", False, "pr-description.md missing"))
    else:
        text = pr.read_text()
        lines = [l for l in text.splitlines() if l.strip()]
        issues = []
        if len(lines) > 20:
            issues.append("%d non-empty lines (>20)" % len(lines))
        if not any(l.startswith("Testing:") for l in lines):
            issues.append("no 'Testing:' line")
        if BULLET_RE.search(text):
            issues.append("bullet lists")
        if re.search(r"- \[[ x]\]", text):
            issues.append("checkboxes")
        if find_emoji(text):
            issues.append("emoji")
        results.append(result(
            "pr_description_matches_mandated_shape", not issues, issues or "shape OK",
        ))

    collateral_emoji = find_emoji(full) + (find_emoji(pr.read_text()) if pr.exists() else [])
    results.append(result(
        "no_emoji_in_collateral", not collateral_emoji, collateral_emoji[:5] or "none",
    ))

    issues = []
    expected_parser = sha(FIXTURE / "fixed" / "src" / "parser.py")
    head_parser = git(repo, "show", "HEAD:src/parser.py")[1]
    if hashlib.sha256(head_parser.encode()).hexdigest() != expected_parser:
        issues.append("src/parser.py at HEAD differs from the provided fix")
    if sha(repo_path / "src" / "parser.py") != expected_parser:
        issues.append("src/parser.py in working tree differs from the provided fix")
    _, committed, _ = git(repo, "diff", BASE, "HEAD", "--name-only")
    extra = sorted(set(committed.split()) - {"src/parser.py", "tests/test_parser.py"})
    if extra:
        issues.append("unsolicited files in commit: %s" % extra)
    _, status, _ = git(repo, "status", "--porcelain")
    dirty = [l for l in status.splitlines() if l.strip() and l[3:] != "pr-description.md"]
    if dirty:
        issues.append("working tree not clean: %s" % dirty)
    _, tracked, _ = git(repo, "ls-tree", "-r", "HEAD", "--name-only")
    if "pr-description.md" in tracked.split():
        issues.append("pr-description.md committed into the repo")
    results.append(result(
        "no_unsolicited_code_changes", not issues, issues or "commit scope exact",
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])

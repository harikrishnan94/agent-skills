#!/usr/bin/env python3
"""Check a review-pr package against the fixed output format in SKILL.md.

Usage: check_review.py <package.md | ->

Prints OK and exits 0, or lists every problem and exits 1. Exits 2 when the
file cannot be read. The format is defined by the template in step 8 of
SKILL.md; keep the two in sync.
"""

import re
import sys
from pathlib import Path

VERDICT_EVENTS = {
    "Request changes": "REQUEST_CHANGES",
    "Comment": "COMMENT",
    "Approve with the suggestions": "APPROVE",
    "Approve": "APPROVE",
}
EVENTS = ("APPROVE", "COMMENT", "REQUEST_CHANGES")

SECTIONS = ["What it does", "Findings", "Not raising", "Draft review", "Review record"]

PARTS = [
    ("Change and gain", r"Change and gain"),
    ("Context", r"Context"),
    ("Problem", r"Problem"),
    ("Before → After", r"Before (?:→|->) After"),
    ("Promises and unchanged", r"Promises and unchanged"),
    ("How the code does it", r"How the code does it"),
    ("Performance", r"Performance"),
    ("Correctness and safety", r"Correctness and safety"),
    ("Interaction", r"Interaction"),
]

# (step number, label, sub-items required when the step is `done`)
RECORD = [
    (1, "Gather", ["Author", "Issues", "CI caused by PR", "Existing reviews",
                   "Repo review skill", "Overlapping PRs"]),
    (2, "Explain", ["Parts n/a"]),
    (3, "Structural passes", ["reduce-complexity", "humanize", "plain-prose"]),
    (4, "Evidence", ["Performance", "Correctness", "Tests", "Description",
                     "Design and scope"]),
    (5, "Verify", ["Re-checked at", "Challenger", "Conflicts", "Labels"]),
    (6, "Choose", ["Row"]),
    (7, "Draft", ["Passes", "Greeting"]),
]
EVIDENCE_STEP = 4

# Only the tokens the template uses, so `std::vector<int>` in a finding is fine.
PLACEHOLDER_RE = re.compile(
    r"<(?:title|N|author|verdict|direct answer|sha|text|finding|what you checked"
    r"|candidate|why|path|line|comment|result|reason|steps|limits)>"
)

SHA = r"(?=[0-9a-f]*\d)[0-9a-f]{7,40}"
TITLE_RE = re.compile(
    r"^## (?P<title>.+) \((?:#(?P<n1>\d+)|\[#(?P<n2>\d+)\]\([^)]*\)) by "
    r"@(?P<author>[\w.\[\]-]+)\): "
    r"(?P<verdict>Request changes|Comment|Approve with the suggestions|Approve)$"
)
HEAD_RE = re.compile(
    rf"^Head: (?P<sha>{SHA}) \(re-checked before presenting: "
    rf"(?:unchanged|moved to {SHA})\)$"
)
DRAFT_HEADING_RE = re.compile(r"^Draft review \(event: (?P<event>[^)]*)\)$")
FINDING_RE = re.compile(r"^- \*\*(?:Blocking|Non-blocking)\b")
COMMENT_ITEM_RE = re.compile(r"^\d+\. ")
COMMENT_ANCHOR_RE = re.compile(r"^\d+\. `[^`\s]+:\d+(?:-\d+)?`")
STEP_RE = re.compile(r"^- \*\*(\d)\.\s+([^*:]+?):?\*\*:?\s*(.*)$")
SUB_RE = re.compile(r"^(\s+)- ([^:]+?):\s*(.*)$")
STATUS_RE = re.compile(r"^(done|n/a|not done)(?::\s*(.*))?$")
EVIDENCE_RE = re.compile(r"^(?:applied:\s*\S.*|n/a:\s*\S.*|not done:\s*\S.*)$")
SHA_RE = re.compile(rf"\b{SHA}\b")


def classify(text):
    """Return (line number, text, inside a code fence) for every line."""
    out, fence = [], None
    for no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        opening = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence is None and opening:
            fence = opening.group(1)
            out.append((no, raw, True))
        elif fence is not None and re.fullmatch(
            re.escape(fence[0]) + "{%d,}" % len(fence), stripped
        ):
            fence = None
            out.append((no, raw, True))
        else:
            out.append((no, raw, fence is not None))
    return out


def is_fence_marker(raw):
    return bool(re.match(r"^\s*(`{3,}|~{3,})", raw))


def split_sections(lines):
    heads = [
        (i, m.group(1).strip())
        for i, (_, raw, fenced) in enumerate(lines)
        if not fenced and (m := re.match(r"^### (.*)$", raw))
    ]
    pre_end = heads[0][0] if heads else len(lines)
    sections = []
    for k, (i, name) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        sections.append((name, lines[i][0], lines[i + 1:end]))
    return lines[:pre_end], sections


def section_key(name):
    if name == "Draft review" or name.startswith("Draft review "):
        return "Draft review"
    return name


def has_text(rest, following):
    """True if `rest` or any following (non-fence-marker) line has content."""
    if rest.strip():
        return True
    return any(raw.strip() and not is_fence_marker(raw) for _, raw, _ in following)


def check_header(pre, problems):
    body = [(no, raw) for no, raw, fenced in pre if raw.strip() and not fenced]
    if not body:
        problems.append("the package is empty or starts inside a code fence")
        return None
    no, first = body[0]
    m = TITLE_RE.match(first)
    verdict = None
    if m:
        verdict = m.group("verdict")
    else:
        problems.append(
            f"line {no}: the first line must be "
            "'## <title> (#<N> by @<author>): <verdict>' with a verdict of "
            "Request changes, Comment, Approve with the suggestions or Approve"
        )
    head_seen = False
    answer = []
    for no, raw in body[1:]:
        if raw.startswith("Head:"):
            head_seen = True
            if not HEAD_RE.match(raw):
                problems.append(
                    f"line {no}: Head must read 'Head: <sha> (re-checked before "
                    "presenting: unchanged | moved to <sha>)' with real SHAs "
                    "(7-40 hex characters) and one of the two outcomes"
                )
        else:
            answer.append(raw)
    if not head_seen:
        problems.append("the Head line is missing between the title and '### What it does'")
    if not answer:
        problems.append("the direct answer is missing between the title and the Head line")
    return verdict, answer[0] if answer else ""


def check_parts(lines, problems):
    found = {}
    for idx, (_, raw, fenced) in enumerate(lines):
        if fenced:
            continue
        for n, (_, rx) in enumerate(PARTS, 1):
            m = re.match(rf"^\s*(?:[-*]\s+)?\*\*{n}\.\s+{rx}\.?\*\*(.*)$", raw)
            if m and n not in found:
                found[n] = (idx, m.group(1))
    for n, (label, _) in enumerate(PARTS, 1):
        if n not in found:
            problems.append(f"What it does: part '**{n}. {label}.**' is missing")
    order = [found[n][0] for n in sorted(found)]
    if order != sorted(order):
        problems.append("What it does: the nine parts are not in order 1 to 9")
    starts = sorted(idx for idx, _ in found.values())
    for n, (idx, rest) in sorted(found.items()):
        later = [s for s in starts if s > idx]
        end = later[0] if later else len(lines)
        if not has_text(rest, lines[idx + 1:end]):
            problems.append(f"What it does: part {n} ({PARTS[n - 1][0]}) has no text")


def list_blocks(lines):
    blocks, stray = [], []
    for no, raw, fenced in lines:
        if not fenced and raw.startswith("- "):
            blocks.append([no, raw, raw])
        elif blocks:
            blocks[-1][2] += "\n" + raw
        elif raw.strip() and not fenced:
            stray.append(no)
    return blocks, stray


def check_list_section(name, lines, problems, findings=False):
    plain = [raw.strip() for _, raw, fenced in lines if raw.strip() and not fenced]
    if plain == ["None."]:
        return
    blocks, stray = list_blocks(lines)
    if stray or not blocks:
        problems.append(f"{name}: write bullets, or the single word 'None.'")
        return
    if not findings:
        return
    for no, first, whole in blocks:
        if not FINDING_RE.match(first):
            problems.append(f"line {no}: a finding must start with '- **Blocking**' or '- **Non-blocking**'")
        if "Evidence:" not in whole:
            problems.append(f"line {no}: a finding must say 'Evidence:' and what you checked")


def check_draft(heading, lines, verdict, problems):
    m = DRAFT_HEADING_RE.match(heading)
    event = m.group("event").strip() if m else None
    if event not in EVENTS:
        problems.append(
            "the Draft review heading must read '### Draft review (event: X)' "
            f"with X one of {', '.join(EVENTS)} (got {heading!r})"
        )
    elif verdict and event != VERDICT_EVENTS[verdict]:
        problems.append(
            f"the verdict '{verdict}' needs event {VERDICT_EVENTS[verdict]}, "
            f"but the Draft review says {event}"
        )
    items = [i for i, (_, raw, fenced) in enumerate(lines)
             if not fenced and COMMENT_ITEM_RE.match(raw)]
    body_at = next((i for i, (_, raw, fenced) in enumerate(lines)
                    if not fenced and raw.startswith("Body:")), None)
    if body_at is None:
        problems.append("Draft review: the 'Body:' line is missing")
    else:
        later = [i for i in items if i > body_at]
        stop = later[0] if later else len(lines)
        rest = lines[body_at][1][len("Body:"):]
        if not has_text(rest, lines[body_at + 1:stop]):
            problems.append("Draft review: the Body has no text")
    for k, i in enumerate(items):
        no, raw, _ = lines[i]
        if not COMMENT_ANCHOR_RE.match(raw):
            problems.append(
                f"line {no}: an inline comment must start with "
                "'N. `path:line`' (or `path:start-end`)"
            )
            continue
        stop = items[k + 1] if k + 1 < len(items) else len(lines)
        if not has_text(COMMENT_ANCHOR_RE.sub("", raw), lines[i + 1:stop]):
            problems.append(f"line {no}: the inline comment has no text")


def parse_record(lines):
    entries, current, sub = {}, None, None
    limits = None
    for no, raw, fenced in lines:
        if fenced:
            if sub is not None and current is not None and raw.strip():
                sub["text"] += " " + raw.strip()
            continue
        if raw.startswith("Verification limits:"):
            limits = {"no": no, "text": raw[len("Verification limits:"):].strip(), "rest": []}
            current = sub = None
            continue
        if limits is not None:
            if raw.strip():
                limits["rest"].append(raw.strip())
            continue
        step = STEP_RE.match(raw)
        sub_item = SUB_RE.match(raw)
        if step:
            n = int(step.group(1))
            current = entries.setdefault(
                n, {"label": step.group(2).strip(), "status": step.group(3).strip(),
                    "no": no, "subs": {}})
            sub = None
        elif current is not None and sub_item and len(sub_item.group(1)) < 4:
            sub = {"name": sub_item.group(2).strip(), "text": sub_item.group(3).strip(), "no": no}
            current["subs"].setdefault(sub["name"].lower(), sub)
        elif sub is not None and raw.strip():
            sub["text"] += " " + raw.strip()
    return entries, limits


def check_record(lines, problems):
    entries, limits = parse_record(lines)
    not_done = False
    for n, label, required in RECORD:
        entry = entries.get(n)
        if entry is None:
            problems.append(f"Review record: step '**{n}. {label}:**' is missing")
            continue
        if entry["label"].lower() != label.lower():
            problems.append(
                f"line {entry['no']}: step {n} must be labelled '{label}', not '{entry['label']}'"
            )
        m = STATUS_RE.match(entry["status"])
        if not m:
            problems.append(
                f"line {entry['no']}: step {n} ({label}) must be followed by "
                "'done', 'n/a: <reason>' or 'not done: <reason>'"
            )
            continue
        status, note = m.group(1), (m.group(2) or "").strip()
        if status != "done" and (not note or PLACEHOLDER_RE.fullmatch(note)):
            problems.append(f"line {entry['no']}: step {n} ({label}) is '{status}' and needs a reason")
        if status == "not done":
            not_done = True
        if status != "done":
            continue
        for item in required:
            sub = entry["subs"].get(item.lower())
            if sub is None:
                problems.append(f"Review record: step {n} ({label}) is missing '{item}:'")
                continue
            text = sub["text"]
            if not text:
                problems.append(f"line {sub['no']}: '{item}' has no result")
            elif n == EVIDENCE_STEP and not EVIDENCE_RE.match(text):
                problems.append(
                    f"line {sub['no']}: '{item}' must start with 'applied: <result>', "
                    "'n/a: <reason>' or 'not done: <reason>'"
                )
            elif item == "Re-checked at" and not SHA_RE.search(text):
                problems.append(f"line {sub['no']}: 'Re-checked at' must give a SHA (7-40 hex characters)")
            elif re.match(r"^n/a\b(?!:\s*\S)", text):
                problems.append(f"line {sub['no']}: '{item}' is n/a and needs a reason")
            if re.match(r"^not done\b", text):
                not_done = True
    if limits is None:
        problems.append("'Verification limits:' is missing after the Review record")
    else:
        last = max((e["no"] for e in entries.values()), default=0)
        if limits["no"] < last:
            problems.append("'Verification limits:' must come after the Review record entries")
        if not limits["text"] and not limits["rest"]:
            problems.append("'Verification limits:' has no text")
    return not_done


def check(text):
    """Return a list of problems; an empty list means the package conforms."""
    problems = []
    lines = classify(text)
    pre, sections = split_sections(lines)
    header = check_header(pre, problems)
    verdict, first_answer = header if header else (None, "")

    keys = [section_key(name) for name, _, _ in sections]
    for key in SECTIONS:
        if key not in keys:
            problems.append(f"the '### {key}' section is missing")
    for name, no, _ in sections:
        if section_key(name) not in SECTIONS:
            problems.append(f"line {no}: unexpected heading '### {name}'; the sections are "
                            + ", ".join(SECTIONS))
    seen = [k for k in keys if k in SECTIONS]
    if seen != sorted(seen, key=SECTIONS.index):
        problems.append("the sections are out of order; they must be " + ", ".join(SECTIONS))

    not_done = False
    for name, _, body in sections:
        key = section_key(name)
        if key == "What it does":
            check_parts(body, problems)
        elif key == "Findings":
            check_list_section("Findings", body, problems, findings=True)
        elif key == "Not raising":
            check_list_section("Not raising", body, problems)
        elif key == "Draft review":
            check_draft(name, body, verdict, problems)
        elif key == "Review record":
            not_done = check_record(body, problems)

    if not_done and not first_answer.startswith("Incomplete:"):
        problems.append(
            "a step is 'not done', so the direct answer must start with "
            "'Incomplete: <steps>.'"
        )

    for no, raw, fenced in lines:
        if not fenced:
            for token in sorted(set(PLACEHOLDER_RE.findall(raw))):
                problems.append(f"line {no}: the template placeholder {token} is still there")
    return problems


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    try:
        text = sys.stdin.read() if argv[1] == "-" else Path(argv[1]).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {argv[1]}: {exc}", file=sys.stderr)
        return 2
    problems = check(text)
    if problems:
        print(f"{len(problems)} problem(s) in the review package:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Write single-file copies of skills, for hosts that load only a SKILL.md.

Usage: single_file.py [skill ...]

Writes dist/single-file/<skill>/SKILL.md for each named skill, or for every
skill in SKILLS. The sources under skills/ are not changed.

A skill's references are appended as sections and its script is embedded in a
fenced block. REWRITES turns each pointer to those files into a pointer to the
section.

The run fails and writes nothing in these cases: a skill has a file that
SKILLS does not list, a pointer that REWRITES expects is gone from the source,
or the copy still names a file or links to a heading it does not have.
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/single-file"

# skill: (references in the order they are appended,
#         (script, section heading, what the script is for, where the agent saves it))
SKILLS = {
    "humanize": ([], None),
    "plain-prose": ([], None),
    "reduce-complexity": ([], None),
    "review-pr": (
        ["clickhouse.md", "evidence.md", "comments.md"],
        ("check_review.py", "Checker script", "Step 8 runs this script.",
         "./tmp/review-pr-<N>/check_review.py"),
    ),
    "watch-pr": (
        ["posting.md", "clickhouse.md", "observer.md"],
        ("observe_pr.py", "Observer script", "This script is the observer.",
         "$STATE_DIR/observe_pr.py"),
    ),
}

# source file: [(text in the source, text in the copy)]
# The source text matches however its paragraph is wrapped.
REWRITES = {
    "review-pr/SKILL.md": [
        ("[references/clickhouse.md](references/clickhouse.md)",
         "[ClickHouse specifics](#clickhouse-specifics)"),
        ("[references/evidence.md](references/evidence.md)",
         "[Evidence checks](#evidence-checks)"),
        ("each section of evidence.md", "each section of Evidence checks"),
        ("evidence.md and ask.", "Evidence checks and ask."),
        ("[references/comments.md](references/comments.md)",
         "[Review comments](#review-comments)"),
        ("Greeting (the comments.md", "Greeting (the Review comments"),
        ("Follow the posting steps in comments.md.",
         "Follow the [posting steps](#posting)."),
        ('2. From that same root, run `python3 "<skill dir>/scripts/check_review.py"\n'
         "   ./tmp/review-pr-<N>/package.md`. Installed copies are symlinks, so resolve\n"
         "   the skill directory with `realpath` first.",
         "2. From that same root, save the checker script as\n"
         "   `./tmp/review-pr-<N>/check_review.py` and check the copy, as\n"
         "   [Checker script](#checker-script) describes. Then run `python3\n"
         "   ./tmp/review-pr-<N>/check_review.py ./tmp/review-pr-<N>/package.md`."),
    ],
    "watch-pr/SKILL.md": [
        ("follow [posting.md](references/posting.md).",
         "follow\n[GitHub comment attribution](#github-comment-attribution)."),
        ("[observer](references/observer.md)", "[observer](#observer)"),
        ("[clickhouse.md](references/clickhouse.md)",
         "[ClickHouse CI rounds](#clickhouse-ci-rounds)"),
        ("[blocker actions](references/observer.md#blocker-actions)",
         "[blocker actions](#blocker-actions)"),
        # A single-file host has no sibling skill directories to fall back to.
        (" If the host cannot load\n"
         "them, use their sibling directories beside this skill.", ""),
    ],
    "watch-pr/references/observer.md": [
        ("Resolve `<skill-dir>` from this skill's installed\n"
         "location, including symlinks; never from the caller's working directory.",
         "First save the script as `$STATE_DIR/observe_pr.py`\n"
         "and check the copy, as [Observer script](#observer-script) describes."),
        ("python3 <skill-dir>/scripts/observe_pr.py",
         'python3 "$STATE_DIR/observe_pr.py"'),
    ],
    "watch-pr/references/clickhouse.md": [
        ("apply the main skill's semantic merge procedure in an isolated",
         "apply the semantic merge procedure from\n"
         "  [Repair while preserving intent](#repair-while-preserving-intent) in an isolated"),
        ("using the\nmain skill's ancestry gate. ",
         "using the\nancestry gate in [Validate and publish](#validate-and-publish).\n"),
    ],
}

SCRIPT_SECTION = """\
## {heading}

{purpose} Save it as `{path}`.

If you can read this SKILL.md as a file, extract the script with `awk`:

```bash
awk '/^```python {pattern}$/ {{on = 1; next}} on && /^```$/ {{exit}} on' \\
  "<path to this SKILL.md>" > "{path}"
```

Otherwise write out the `python {script}` block at the end of this section.
Copy it exactly as it appears, without its two fence lines.

Then check the copy. This command must print `{digest}`:

```bash
python3 -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read().strip()).hexdigest())' \\
  "{path}"
```

Any other output means the copy differs from the block. Save it again.

```python {script}
{source}```
"""

POINTER_RE = re.compile(r"references/|scripts/|skill[- ]dir|\]\((?!https?://|#)")
# Spaces with at most one line break: the gap between two words of a paragraph.
WRAP = r"(?:[ \t]*\n[ \t]*|[ \t]+)"


class Problem(Exception):
    """A skill's sources no longer match SKILLS or REWRITES."""


def fenced(lines):
    """Yield (line, inside a code fence) for each line."""
    fence = None
    for line in lines:
        stripped = line.strip()
        opening = re.match(r"`{3,}|~{3,}", stripped)
        if fence is None and opening:
            fence = opening.group()
            yield line, True
        elif fence and stripped.startswith(fence) and not stripped.strip(fence[0]):
            fence = None
            yield line, True
        else:
            yield line, fence is not None


def demote(text):
    """Push headings one level down, so a reference's title becomes a section."""
    return "".join(
        "#" + line if not inside and re.match(r"#{1,5} ", line) else line
        for line, inside in fenced(text.splitlines(keepends=True))
    )


def rewritten(name, relative):
    text = (ROOT / "skills" / name / relative).read_text(encoding="utf-8")
    for old, new in REWRITES.get(f"{name}/{relative}", []):
        pattern = WRAP.join(re.escape(word) for word in re.split(r"\s+", old))
        text, count = re.subn(pattern, lambda _: new, text)
        if not count:
            raise Problem(f"{name}/{relative} no longer contains {old!r}; update REWRITES")
    return text


def script_section(name, script, heading, purpose, path):
    source = (ROOT / "skills" / name / "scripts" / script).read_text(encoding="utf-8")
    if any(inside for _, inside in fenced(source.splitlines())):
        raise Problem(f"{name}: {script} has a line that would close its code fence")
    return SCRIPT_SECTION.format(
        heading=heading, purpose=purpose, path=path, script=script,
        pattern=script.replace(".", r"\."), source=source,
        digest=hashlib.sha256(source.encode().strip()).hexdigest(),
    )


def missing_anchors(text):
    lines = [line for line, inside in fenced(text.splitlines()) if not inside]
    headings = {
        re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
        for line in lines if (match := re.match(r"#{1,6} +(.+)", line))
    }
    links = {anchor for line in lines for anchor in re.findall(r"\]\(#([^)]+)\)", line)}
    return sorted(links - headings)


def build(name):
    references, script = SKILLS[name]
    skill = ROOT / "skills" / name
    expected = [f"references/{reference}" for reference in references]
    if script:
        expected.append(f"scripts/{script[0]}")
    found = [
        str(path.relative_to(skill)) for path in skill.rglob("*")
        if path.is_file() and path.name not in ("SKILL.md", ".DS_Store")
        and "__pycache__" not in path.parts
    ]
    if sorted(found) != sorted(expected):
        raise Problem(f"{name}: SKILLS lists {sorted(expected)}, but the skill has {sorted(found)}")

    parts = [rewritten(name, "SKILL.md")]
    parts += [demote(rewritten(name, f"references/{reference}")) for reference in references]
    text = "\n".join(part.strip("\n") + "\n" for part in parts)
    stale = [line for line in text.splitlines()
             if POINTER_RE.search(line) or any(reference in line for reference in references)]
    if stale:
        raise Problem(f"{name}: the copy still points at a file; add these to REWRITES:\n"
                      + "\n".join(stale))
    if script:
        text += "\n" + script_section(name, *script)
    missing = missing_anchors(text)
    if missing:
        raise Problem(f"{name}: the copy links to headings it does not have: {missing}")
    return text


def main(argv):
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print(__doc__.strip())
        return 0
    names = argv[1:] or list(SKILLS)
    unknown = [name for name in names if name not in SKILLS]
    if unknown:
        print(f"no entry in SKILLS for: {', '.join(unknown)}", file=sys.stderr)
        return 2
    try:
        texts = {name: build(name) for name in names}
    except Problem as problem:
        print(f"{problem}\nNo copy was written.", file=sys.stderr)
        return 1
    for name, text in texts.items():
        path = OUT / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: {len(text.splitlines())} lines, {len(text.encode())} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Assertions for the fixmode-burst-limits-cleanup eval. Usage: check_fixmode.py <repo>"""

import ast
import subprocess
import sys
from pathlib import Path

from common import emit, find_emoji, git, result, run_tests

RESTATING = [
    "# get the client ip from the request",
    "# store the bucket",
    "# loop over the range of n",
    "# increment the counter by one",
    "# read the config file from the path",
    "# something went wrong so just use defaults",
]
LOAD_BEARING = {
    "ratelimit/bucket.py": "# key -> (tokens, last_ts)",
    "ratelimit/middleware.py": "absent or None",
}


def main(repo):
    repo_path = Path(repo)
    results = []

    tree = ast.parse((repo_path / "ratelimit" / "config.py").read_text())
    broad = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == "load_cfg":
            for node in ast.walk(fn):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None or (
                        isinstance(node.type, ast.Name) and node.type.id == "Exception"
                    ):
                        broad.append(ast.dump(node.type) if node.type else "bare except")
    results.append(result(
        "dead_defensive_catch_removed", not broad, broad or "no broad handler in load_cfg",
    ))

    probe = Path(__file__).with_name("probe_guard.py")
    p = subprocess.run(
        [sys.executable, str(probe), repo], capture_output=True, text=True, timeout=60
    )
    results.append(result(
        "real_edge_guard_added",
        p.returncode == 0,
        (p.stdout + p.stderr).strip()[-800:],
    ))

    still_restating, missing_lb = [], []
    py_text = {
        str(f.relative_to(repo_path)): f.read_text()
        for f in repo_path.rglob("*.py")
        if ".git" not in f.parts
    }
    all_py = "\n".join(py_text.values())
    for s in RESTATING:
        if s in all_py:
            still_restating.append(s)
    for f, s in LOAD_BEARING.items():
        if s not in py_text.get(f, ""):
            missing_lb.append("%s: %r" % (f, s))
    results.append(result(
        "restating_comments_gone_load_bearing_kept",
        not still_restating and not missing_lb,
        "restating left: %s; load-bearing lost: %s" % (still_restating, missing_lb)
        if still_restating or missing_lb else "all planted strings gone, anchors kept",
    ))

    classes, has_burst = [], False
    for f, text in py_text.items():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ClassDef) and node.name == "BurstLimitManager":
                classes.append(f)
            if isinstance(node, ast.FunctionDef) and node.name == "check_burst":
                has_burst = True
    results.append(result(
        "wrapper_class_flattened",
        not classes and has_burst,
        "BurstLimitManager in: %s; check_burst exists: %s" % (classes, has_burst),
    ))

    _, tracked, _ = git(repo, "ls-tree", "-r", "HEAD", "--name-only")
    in_head = "SUMMARY.md" in tracked.split()
    on_disk = (repo_path / "SUMMARY.md").exists()
    results.append(result(
        "summary_md_deleted",
        not in_head and not on_disk,
        "in HEAD: %s; on disk: %s" % (in_head, on_disk),
    ))

    rc, out = run_tests(repo)
    api_ok, api_err = True, ""
    p = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from ratelimit.bucket import TokenBucket; "
         "from ratelimit.middleware import parse_client, check, check_burst; "
         "from ratelimit.config import load_cfg",
         repo],
        capture_output=True, text=True, timeout=60,
    )
    if p.returncode != 0:
        api_ok, api_err = False, p.stderr[-400:]
    results.append(result(
        "no_behavior_change",
        rc == 0 and api_ok,
        ("unittest OK" if rc == 0 else out) + ("" if api_ok else "; import failed: " + api_err),
    ))

    emoji = find_emoji(all_py)
    _, churn, _ = git(repo, "diff", "main", "--", "ratelimit/bucket.py")
    results.append(result(
        "no_emoji_and_reformat_churn_reverted",
        not emoji and not churn.strip(),
        "emoji: %s; bucket.py still differs from main: %s"
        % (emoji[:5], bool(churn.strip())),
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])

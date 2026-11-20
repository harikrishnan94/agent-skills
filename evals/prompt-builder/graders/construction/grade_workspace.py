"""Grade every construction run in a workspace directory.

Usage: python3 grade_workspace.py <workspace-construction-dir>

Expects <dir>/eval-NN-<slug>/<config>/run-N/outputs/generated-prompt.md and
writes grading.json (expectations format, no timing key) next to each run's
outputs/. Prints a per-run summary table and per-class pass rates per config
(classes from evals.json assertion_classes; DESIGN.md §2 forbids pooling).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS_JSON = HERE.parents[1] / "evals.json"


def main():
    ws = Path(sys.argv[1])
    manifest = json.loads(EVALS_JSON.read_text())
    classes = manifest["assertion_classes"]
    def clazz(assertion):
        for c, names in classes.items():
            if assertion in names:
                return c
        return "skill-feature"  # profile knobs default

    rows = []
    class_tally = {}  # (config, class) -> [passed, total]
    for evdir in sorted(ws.glob("eval-*")):
        m = re.match(r"eval-(\d+)-", evdir.name)
        if not m:
            continue
        brief_id = int(m.group(1))
        for cfgdir in sorted(evdir.iterdir()):
            if not cfgdir.is_dir():
                continue
            for rundir in sorted(cfgdir.glob("run-*")):
                prompt = rundir / "outputs" / "generated-prompt.md"
                if not prompt.exists():
                    rows.append((evdir.name, cfgdir.name, rundir.name, "MISSING", ""))
                    continue
                p = subprocess.run(
                    [sys.executable, str(HERE / "check_prompt.py"),
                     str(brief_id), str(prompt)],
                    capture_output=True, text=True)
                expectations = json.loads(p.stdout)
                npass = sum(1 for e in expectations if e["passed"])
                (rundir / "grading.json").write_text(json.dumps(
                    {"expectations": expectations,
                     "summary": {
                         "passed": npass,
                         "failed": len(expectations) - npass,
                         "total": len(expectations),
                         "pass_rate": round(npass / len(expectations), 4)
                         if expectations else 0.0}},
                    indent=1))
                for e in expectations:
                    key = (cfgdir.name, clazz(e["text"]))
                    class_tally.setdefault(key, [0, 0])
                    class_tally[key][1] += 1
                    class_tally[key][0] += bool(e["passed"])
                failed = [e["text"] for e in expectations if not e["passed"]]
                rows.append((evdir.name, cfgdir.name, rundir.name,
                             "%d/%d" % (len(expectations) - len(failed),
                                        len(expectations)),
                             ",".join(failed)))

    for r in rows:
        print("%-38s %-14s %-6s %-6s %s" % r)
    print()
    print("Per-class pass rates (DESIGN §2: never pooled):")
    for (cfg, c), (ok, tot) in sorted(class_tally.items()):
        print("  %-14s %-18s %3d/%3d  (%.0f%%)" % (cfg, c, ok, tot, 100 * ok / tot))


if __name__ == "__main__":
    main()

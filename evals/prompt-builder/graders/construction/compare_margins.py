"""Pre-registered §6 margins check: candidate arm vs current-skill baseline.

Usage: python3 compare_margins.py <workspace-construction-dir> <candidate-config> [<baseline-config>=with_skill]

Reads each run's grading.json + generated prompt, and reports per DESIGN §6:
- per-class pass counts (hygiene / skill-feature / template-disposal)
- per-assertion brief-loss counts (rule: no assertion loses >1 brief; a
  1-brief loss triggers one regeneration before it counts)
- names_runnable_oracle / names_refuting_verifier strictly-better-or-hold-at-100
- right-sizing: median words per scale class (tiny/small strictly lower,
  never higher on any class)
Exit 0 iff all margins pass (regeneration triggers reported, not fatal).
"""

import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = json.loads((HERE.parents[1] / "evals.json").read_text())
CLASSES = EVALS["assertion_classes"]
BRIEFS = {b["id"]: b for b in EVALS["tracks"]["construction"]["briefs"]}


def clazz(name):
    for c, names in CLASSES.items():
        if name in names:
            return c
    return "skill-feature"


def load(ws, config):
    runs = {}
    for evdir in sorted(ws.glob("eval-*")):
        bid = int(re.match(r"eval-(\d+)-", evdir.name).group(1))
        g = evdir / config / "run-1" / "grading.json"
        p = evdir / config / "run-1" / "outputs" / "generated-prompt.md"
        if not g.exists():
            print(f"MISSING grading: {evdir.name}/{config}")
            continue
        exp = {e["text"]: e["passed"] for e in json.loads(g.read_text())["expectations"]}
        words = len(p.read_text().split()) if p.exists() else None
        runs[bid] = {"exp": exp, "words": words}
    return runs


def main():
    ws = Path(sys.argv[1])
    cand_cfg = sys.argv[2]
    base_cfg = sys.argv[3] if len(sys.argv) > 3 else "with_skill"
    base, cand = load(ws, base_cfg), load(ws, cand_cfg)
    ok = True

    print(f"=== per-class counts ({cand_cfg} vs {base_cfg})")
    for c in CLASSES:
        bt = bp = ct = cp = 0
        for bid in base:
            for a, v in base[bid]["exp"].items():
                if clazz(a) == c:
                    bt += 1; bp += bool(v)
            for a, v in cand.get(bid, {"exp": {}})["exp"].items():
                if clazz(a) == c:
                    ct += 1; cp += bool(v)
        print(f"  {c:<18} candidate {cp}/{ct}  baseline {bp}/{bt}")

    print("=== per-assertion brief losses (rule: >1 lost brief fails; 1 → regenerate)")
    assertions = sorted({a for r in base.values() for a in r["exp"]})
    regen = []
    for a in assertions:
        lost = [bid for bid in base
                if base[bid]["exp"].get(a) is True
                and cand.get(bid, {"exp": {}})["exp"].get(a) is False]
        gained = [bid for bid in base
                  if base[bid]["exp"].get(a) is False
                  and cand.get(bid, {"exp": {}})["exp"].get(a) is True]
        if lost or gained:
            print(f"  {a:<36} lost {lost} gained {gained}")
        if len(lost) > 1:
            print(f"    ** MARGIN FAIL: {a} loses {len(lost)} briefs")
            ok = False
        elif len(lost) == 1:
            regen.append((a, lost[0]))

    print("=== strictly-better gates")
    for a in ["names_runnable_oracle", "names_refuting_verifier"]:
        b = sum(1 for bid in base if base[bid]["exp"].get(a) is True)
        c_ = sum(1 for bid in cand if cand[bid]["exp"].get(a) is True)
        n = sum(1 for bid in base if a in base[bid]["exp"])
        verdict = "HOLD-AT-100 ok" if b == n and c_ == n else (
            "STRICTLY BETTER ok" if c_ > b else "** MARGIN FAIL")
        if "FAIL" in verdict:
            ok = False
        print(f"  {a:<36} candidate {c_}/{n}  baseline {b}/{n}  {verdict}")

    print("=== right-sizing (median words per scale class)")
    for scale in ["tiny", "small", "medium", "large"]:
        bids = [bid for bid, b in BRIEFS.items() if b["scale"] == scale]
        bw = [base[bid]["words"] for bid in bids if base.get(bid, {}).get("words")]
        cw = [cand[bid]["words"] for bid in bids if cand.get(bid, {}).get("words")]
        if not bw or not cw:
            continue
        bm, cm = statistics.median(bw), statistics.median(cw)
        need_lower = scale in ("tiny", "small")
        bad = (cm >= bm) if need_lower else (cm > bm)
        if bad:
            ok = False
        print(f"  {scale:<7} candidate median {cm:.0f}  baseline {bm:.0f}  "
              f"{'** MARGIN FAIL' if bad else 'ok'}"
              f"{' (must be strictly lower)' if need_lower else ''}")

    if regen:
        print("REGENERATION TRIGGERS (1-brief losses — rerun these briefs once "
              "before counting):")
        for a, bid in regen:
            print(f"  {a} on brief {bid} ({BRIEFS[bid]['slug']})")
    print("MARGINS:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

"""Deterministic grader for the prompt-builder construction track.

Usage: python3 check_prompt.py <brief_id> <generated_prompt.md>

Loads the brief's metadata from evals.json (sibling of graders/), runs the
generic + conditional assertions pre-registered in DESIGN.md §2, and prints a
JSON array of {"text", "passed", "evidence"} objects (grading.json
expectations format). Exit 0 iff all assertions pass.

Arm-fairness rule: every pattern is concept-level English, never the skill's
private vocabulary — a genuinely good no-skill prompt can pass everything.
"""

import json
import re
import sys
from pathlib import Path

EVALS_JSON = Path(__file__).resolve().parents[2] / "evals.json"

# Primary proportionality metric is WORDS (line counts reward dense paragraphs
# and are gameable by line-joining — DESIGN.md §2). Lines logged as secondary.
SCALE_WORD_LIMITS = {"tiny": 700, "small": 1400, "medium": 3200, "large": 6500}


def blocks(text):
    """Blank-line-separated chunks; a list runs as one block."""
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


# --- hygiene ---------------------------------------------------------------

SLOT_RE = re.compile(r"<<[^<>\n]{0,120}?>>")
BUILDER_NOTE_RE = re.compile(r"^\s*>?\s*>\s*BUILDER\b|^\s*>\s*BUILDER\b", re.M)

# NOTE: deliberately does NOT match "overnight"/"while offline" — briefs convey
# mode situationally, and echoing the brief is not autonomy handling (DESIGN §2).
UNATTENDED_RE = re.compile(
    r"\b(unattended|autonomous(ly)?|"
    r"without (further |a |any )?(human|user|operator|external)[ -]?"
    r"(input|intervention|approval|help|interaction)|"
    r"no (human|user|one|reviewer) (is |will be )?(available|watching|around|monitoring)|"
    r"do(es)? not (wait|block|pause|stall) (for|on) (a |the )?(human|user|person|response|answer)|"
    r"cannot ask (the )?(user|anyone|a human)|"
    r"proceed (on|with) (your|the|its) (own|best)|"
    r"(record|document|log)[^.\n]{0,40}assumptions?|"
    r"self[- ](directed|sufficient)|no one to ask|"
    r"(make|exercise)[^.\n]{0,30}(judgment|judgement|best call)[^.\n]{0,40}"
    r"(proceed|continue|move on)|"
    r"do not (stop|halt|stall)[^.\n]{0,40}(question|decision|input))\b",
    re.I,
)
INTERACTIVE_RE = re.compile(
    r"\b((ask|check with|confirm with|clarify with|consult) (the )?"
    r"(user|me|owner|requester|human|author)|"
    r"if (unsure|uncertain|ambiguous|in doubt|unclear)[^.\n]{0,80}\bask|"
    r"pause[^.\n]{0,40}(input|confirmation|approval|answer)|"
    r"(user|owner|maintainer|requester|human)[^.\n]{0,24}"
    r"(is |will be )?(available|around|reachable|at (his|her|their) desk)|"
    r"surface[^.\n]{0,60}(question|decision|choice)s? to|"
    r"ask (questions|for clarification|before|him|her|them)|pause and ask|"
    r"blocker[^.\n]{0,80}\bask|"
    r"wait for (an? )?(answer|response|approval))\b",
    re.I,
)

SCOPE_RE = re.compile(
    r"\b(out[- ]of[- ]scope|in[- ]scope|non[- ]goals?|"
    r"(do|does|must|should|will) not (change|modify|touch|alter|edit|refactor|rewrite|introduce|delete|remove|drop|relitigate)|"
    r"never (change|modify|touch|delete|remove|drop|alter)|"
    r"denylist|allowlist|"
    r"leave[^.\n]{0,60}(unchanged|untouched|as[- ]is|alone)|"
    r"not (part of|included in) (this|the) (task|scope|work)|"
    r"only (change|modify|touch|edit)|scope\s*[:—-]|limit (changes|edits|the diff) to)\b",
    re.I,
)

HONEST_FAILURE_RE = re.compile(
    r"\b(no[- ]result|unsettled|inconclusive|cannot be (determined|settled|established|answered)|"
    r"if (you|it|the agent) (cannot|can.t|fail(s)? to|is unable to)[^.\n]{0,120}"
    r"(report|say|state|document|record|return|explain)|"
    r"report[^.\n]{0,40}(honestly|as (open|unresolved|unknown|unsettled|inconclusive))|"
    r"rather than (fabricat|guess|invent|manufactur|overstat)[a-z]*|"
    r"do(es)? not (fabricate|invent|manufacture|overstate|pretend|paper over|hide)|"
    r"admit (uncertainty|failure|defeat|that)|honest(ly)? (report|state|about)|"
    r"unresolved[^.\n]{0,40}(report|document|state)|"
    r"open (questions?|items?)[^.\n]{0,40}(report|list|document)|"
    r"partial (result|success|answer)[^.\n]{0,60}(report|acceptable|return)|"
    r"(negative|null) result[^.\n]{0,80}(successful|valid|acceptable|legitimate|outcome)|"
    r"if you cannot (fix|resolve|identify|determine|answer|demonstrate)|"
    r"cannot (fix|identify|resolve|determine|demonstrate)[^.\n]{0,140}"
    r"(document|report|recommend|note|write|say)|"
    r"do(es)? not thrash)\b",
    re.I,
)

# --- mechanical forcing ----------------------------------------------------

# A backticked or code-fenced token that reads as an executable command.
COMMAND_TOKEN = (
    r"(python[0-9.]*\s+-m\s+\S+[^`\n]*|python[0-9.]*\s+\S+\.py[^`\n]*|"
    r"pytest\b[^`\n]*|unittest\b[^`\n]*|"
    r"npm (test|run)\b[^`\n]*|npx \S+[^`\n]*|make \S+[^`\n]*|cargo \S+[^`\n]*|"
    r"go test\b[^`\n]*|\./\S+[^`\n]*|(bash|sh) \S+\.sh[^`\n]*|scripts?/\S+[^`\n]*|"
    r"mvn \S+[^`\n]*|gradle \S+[^`\n]*|ruff\b[^`\n]*|flake8\b[^`\n]*|eslint\b[^`\n]*|"
    r"playwright\b[^`\n]*|kubectl \S+[^`\n]*|gh \S+[^`\n]*|git \S+[^`\n]*|"
    r"time \S+[^`\n]*|wc \S+[^`\n]*|grep \S+[^`\n]*|curl \S+[^`\n]*|"
    r"manage\.py \S+[^`\n]*|docker \S+[^`\n]*|pip \S+[^`\n]*)"
)
INLINE_CMD_RE = re.compile(r"`\s*" + COMMAND_TOKEN + r"\s*`", re.I)
FENCE_CMD_RE = re.compile(r"```[a-z]*\n[^`]*?" + COMMAND_TOKEN, re.I)
# Unformatted commands count too (review fix: backticks are a formatting habit,
# not a concept) — "run python3 -m unittest before declaring done" is an oracle.
BARE_CMD_RE = re.compile(
    r"\b(run(ning)?|execute|invoke|via|using|with)\s+" + COMMAND_TOKEN, re.I
)

GATE_LANG_RE = re.compile(
    r"\b(must (pass|be green|succeed|exit (0|zero|cleanly))|passes (before|prior)|"
    r"exit(s)? (code )?(0|zero)|green (before|prior|gate)|"
    r"before (declaring|claiming|marking|reporting|considering)[^.\n]{0,40}"
    r"(done|complete|success|fixed|finished)|"
    r"(is|are) (not )?(done|complete|finished) (until|unless|only when)|"
    r"acceptance (criteri|test|check|gate)|definition of done|success criteri|"
    r"completion (gate|criteri|check)|correctness (gate|oracle|check)|oracle|"
    r"verif(y|ied|ication)[^.\n]{0,40}(pass|green|succeed)|"
    r"confirm[^.\n]{0,60}(pass(es)?|green|succeed)|"
    r"fail(s|ure)?[^.\n]{0,40}(block|means|do not (proceed|ship|return))|"
    r"re[- ]?run[^.\n]{0,40}(until|confirm)|regression (suite|test|check)s?[^.\n]{0,40}"
    r"(pass|green|clean))\b",
    re.I,
)

CHECKLIST_ORACLE_RE = re.compile(
    r"\b(checklist|check[- ]?list|"
    r"(each|every|all) (item|requirement|criterion|criteria|claim|procedure|step|"
    r"breaking change|vendor)s?[^.\n]{0,80}"
    r"(check(ed)?|verif|confirm|validated?|traced|covered|scored|graded)|"
    r"word count|`wc|line count|"
    r"(pass|fail)[^.\n]{0,40}(per|for each|criterion|item)|"
    r"scor(e|ing) (sheet|matrix|table|rubric)|"
    r"crosscheck(ed)? against|checked against (the )?"
    r"(requirements?|matrix|spec|source))\b",
    re.I,
)

VERIFIER_RE = re.compile(
    r"\b((fresh|clean|separate|independent|new|second|different)[- ]"
    r"(context|session|agent|subagent|sub-agent|instance|reviewer|model|pair of eyes)|"
    r"(adversarial|red[- ]team|skeptical|hostile)[^.\n]{0,30}"
    r"(review|verif|pass|check|audit)|"
    r"(reviewer|verifier|auditor|second agent|another agent|separate agent|subagent)"
    r"[^.\n]{0,140}(refute|disprove|falsify|prove[^.\n]{0,20}wrong|attack|break|"
    r"poke holes|tear (it )?apart|find (flaws|holes|problems)|assume[^.\n]{0,40}"
    r"(wrong|broken|over[- ]?optimistic|fails))|"
    r"(did|has|have) not (do(ne)?|writ(e|ten)|implement(ed)?)[^.\n]{0,40}"
    r"(work|change|code)[^.\n]{0,60}(review|verif|check)|"
    r"review(er)?[^.\n]{0,60}(must|should) not be the (author|implementer|doer|"
    r"same (agent|model|session))|"
    r"(spawn|launch|use|delegate to)[^.\n]{0,40}(subagent|sub-agent|separate agent)"
    r"[^.\n]{0,80}(review|verif|check))\b",
    re.I,
)

PREREG_RE = re.compile(
    r"\b(pre[- ]?regist(er|ered|ration)|"
    r"before ((you |it |the agent )?(start|begin|touch|implement|act|proceed"
    r"|mak|writ|chang)[a-z]*|each (change|unit|step))"
    r"(?:[^.\n]|\.(?=\w)){0,120}"
    r"(write (down|out)?|record|state|document|note)(?:[^.\n]|\.(?=\w)){0,80}"
    r"(expect|predict|hypothes|outcome|criteria)|"
    r"(write (down|out)?|record|state|document)[^.\n]{0,80}"
    r"(expected (outcome|result|behavior|effect)|prediction|hypothes)"
    r"[^.\n]{0,60}(before|first|prior|up front|upfront)|"
    r"predict(ion)?s?[^.\n]{0,60}(before|first|prior|then (measure|implement|test))|"
    r"state[^.\n]{0,40}(what|how)[^.\n]{0,60}(confirm|refute)[^.\n]{0,40}before|"
    r"(write down|record|document|note)[^.\n]{0,120}"
    r"before (changing|touching|modifying|doing) any|"
    r"decision rule|"
    r"sanity (gates?|checks?|thresholds?)[^.\n]{0,120}abort|"
    r"abort[^.\n]{0,60}(entirely|deletion|the (run|phase|task))[^.\n]{0,80}if|"
    r"abort[^.\n]{0,40}if any of|"
    r"pre[- ]?commit(ted)?[^.\n]{0,60}(threshold|abort|criteri|expectation|rule))\b",
    re.I,
)

# --- profile knobs ----------------------------------------------------------

NEGATIVE_CASE_RE = re.compile(
    r"\b((negative|invalid|failure|error|edge|unhappy|bad|malformed|rejected?)"
    r"[- ]?(case|path|input|scenario)s?[^.\n]{0,100}"
    r"(test|cover|exercise|assert|verif|check|includ|catch|guard)[a-z]*|"
    r"(test|cover|exercise|assert|verif|check|includ)[a-z]*[^.\n]{0,100}"
    r"(negative|invalid|failure|error|edge|unhappy|bad|malformed)"
    r"[- ]?(case|path|input|scenario)s?|"
    r"(invalid|bad|malformed) inputs?[^.\n]{0,60}(fail|reject|error)[a-z]*|"
    r"test[^.\n]{0,60}(what|that)[^.\n]{0,40}should (not|fail|reject))\b",
    re.I,
)

BASELINE_FRESH_RE = re.compile(
    r"\b(baselines?[^.\n]{0,100}(measure|record|establish|capture|take|runs?|first|"
    r"before|fresh|re[- ]?establish)[a-z]*|"
    r"(measure|record|establish|capture)[a-z]*[^.\n]{0,60}baselines?|"
    r"(measure|benchmark|profile|time)[^.\n]{0,60}"
    r"(before (any|making|changing|optimizing)|current|existing|as[- ]is|first)|"
    r"current (performance|timing|latency|runtime|speed)[^.\n]{0,60}"
    r"(measure|record|establish|capture|document)|"
    r"before[- ]and[- ]after|before/after)\b",
    re.I,
)
REGRESSION_FLOOR_RE = re.compile(
    r"\b(no ([a-z]+ )?regressions?|must not (regress|slow|degrade|break|"
    r"get (slower|worse))|must[- ]hold( floor)?|"
    r"regression (check|floor|budget|test|suite|gate)|"
    r"at least as (fast|good)|no(t)? (slower|worse) than|"
    r"without (regressing|degrading|breaking)|"
    r"(previously[- ]passing|existing|all) tests?[^.\n]{0,40}(must |should )?"
    r"(still )?(pass|green)|"
    r"(did|do(es)?|must|should) not (degrade|regress)|"
    r"still pass(es)?|"
    r"(hold|keep|preserve)[^.\n]{0,40}(current|existing)[^.\n]{0,30}"
    r"(behavior|performance|correctness))\b",
    re.I,
)
NOISE_RE = re.compile(
    r"\b(noise|noisy|variance|jitter|"
    r"(multiple|several|repeated|[3-9]\+?|three|five) (runs|measurements|samples|"
    r"iterations|trials)|"
    r"median|mean|average of|stdev|standard deviation|"
    r"±|\+/-|run[- ]to[- ]run|statistical(ly)?|confidence interval|"
    r"within (the )?(noise|error|variance)|outlier)\b",
    re.I,
)

HYPOTHESIS_RE = re.compile(
    r"\b(hypothes[ei]s|root[- ]cause|candidate (cause|explanation)s?|theor(y|ies)|"
    r"suspected (cause|mechanism|fault)|possible (cause|culprit|explanation)s?|"
    r"fault model)\b",
    re.I,
)
REFUTE_RE = re.compile(
    r"\b(refute|falsify|disprove|rule[sd]? out|ruling out|contradict|"
    r"(what|evidence)[^.\n]{0,40}would (disprove|refute|rule (it|this) out|"
    r"prove[^.\n]{0,20}wrong)|"
    r"alternative explanations?|competing (hypothes|explanation)|"
    r"disconfirm|counter[- ]?(evidence|example)|eliminate[^.\n]{0,30}"
    r"(hypothes|candidate|cause))\b",
    re.I,
)

CRITERIA_FIRST_RE = re.compile(
    r"\b((define|fix|set|write|establish|lock|commit to|decide)[^.\n]{0,60}"
    r"(criteria|rubric|scoring|weights?|yardstick|framework)[^.\n]{0,80}"
    r"(before|prior to|first|up front|upfront|then)|"
    r"(criteria|rubric|scoring|weights?)[^.\n]{0,80}"
    r"(before|prior to)[^.\n]{0,60}(scor|evaluat|compar|examin|look|research)|"
    r"pre[- ]?(defin|register|commit)[^.\n]{0,60}(criteria|rubric|scoring|weights?)|"
    r"before (scoring|evaluating|comparing|researching)[^.\n]{0,80}"
    r"(criteria|rubric|weights?)|"
    r"(criteria|rubric)[^.\n]{0,60}(first|up front|upfront)|"
    r"(do not|don.t|never)[^.\n]{0,40}(add|substitute|change|swap|alter|invent)"
    r"[^.\n]{0,30}criteri|"
    r"criteri(a|on)[^.\n]{0,60}(required|fixed|frozen|final|locked|non[- ]negotiable)|"
    r"so (the|a) (conclusion|recommendation|answer)[^.\n]{0,60}"
    r"(can.?t|cannot)[^.\n]{0,40}(pick|choose|select))\b",
    re.I,
)

SOURCED_CLAIMS_RE = re.compile(
    r"\b((cite|citation|source|reference|trace|ground|verif)[a-z]*[^.\n]{0,80}"
    r"(claim|statement|fact|step|procedure|assertion|section|change)s?|"
    r"(every|each|all) (claim|fact|procedure|step|statement|breaking change|item)s?"
    r"[^.\n]{0,100}(source|cite|reference|verified against|grounded|traced|"
    r"checked against|backed)|"
    r"fact[- ]?check|no (unsourced|unverified|guessed) "
    r"(claim|step|procedure|statement)|"
    r"(claim|procedure|step)s?[^.\n]{0,60}(must|should)[^.\n]{0,40}"
    r"(cit|source|traced|grounded|verified))\b",
    re.I,
)

REPRO_FIRST_RE = re.compile(
    r"\b((reproduce|reproduction|repro)[a-z]*[^.\n]{0,120}"
    r"(before|first|prior|then (fix|diagnose|investigate))|"
    r"(first|before)[^.\n]{0,60}(reproduce|reproduction|repro)\b|"
    r"failing (test|case|reproduction|repro)[^.\n]{0,60}"
    r"(first|before|prior|then)|"
    r"(write|create|build)[^.\n]{0,60}(failing|red)[^.\n]{0,60}"
    r"(test|case|repro|harness|configuration)[^.\n]{0,80}(before|first|then|apply)|"
    r"(defect|bug|failure|crash) (demonstrated|shown|made|goes|turned) red|"
    r"red (before|first)[^.\n]{0,20}(the )?(fix|chang|patch)?|"
    r"(show|demonstrate)[a-z]*[^.\n]{0,30}(it |the )?red[^.\n]{0,80}(before|then|apply)|"
    r"confirm[^.\n]{0,50}(bug|defect|failure|crash|issue)[^.\n]{0,60}"
    r"before (fix|chang|patch)|"
    r"(gather|collect|capture|pin down)[^.\n]{0,60}(failure|error|evidence)"
    r"[^.\n]{0,80}before (changing|touching|modifying|any (fix|change))|"
    r"(failure|error|evidence)[^.\n]{0,60}\(do this before changing anything\)|"
    r"(root cause|failure mode)[^.\n]{0,60}(identified|pinned|established)"
    r"[^.\n]{0,40}from (actual|real)[^.\n]{0,20}(logs?|runs?|failures?)|"
    r"reproduce (it|the (bug|crash|issue|failure|defect|problem)))\b",
    re.I,
)
REGRESSION_CHECK_RE = re.compile(
    r"\b(regression(s)? (test|suite|check|oracle)?|"
    r"(existing|full|whole|entire|rest of the) (test )?suite[^.\n]{0,40}"
    r"(pass|green|still|run)|"
    r"no (new|adjacent|other) (breakage|failures?|defects?|regressions?)|"
    r"nothing else (breaks|broke|regressed)|"
    r"do not (disable|weaken|skip|remove)[^.\n]{0,50}"
    r"(job|test|check|suite|matrix|gate)|"
    r"(job|suite|tests?|checks?)[^.\n]{0,50}pass(es)?[^.\n]{0,40}"
    r"(after|on (that|the) (branch|change))|"
    r"after (the|your) (change|fix)[^.\n]{0,80}(pass|green|no regress|still)|"
    r"(does|do|did) not break (anything|other|existing))\b",
    re.I,
)

AUTHORITY_RE = re.compile(
    r"\b((do not|don.t|never|must not)[^.\n]{0,80}"
    r"(delete|drop|destroy|remove|force[- ]push|truncate|purge|wipe)|"
    r"read[- ]only|dry[- ]run|"
    r"(require|obtain|get|wait for|needs?)[^.\n]{0,50}"
    r"(approval|authorization|confirmation|sign[- ]?off|human)|"
    r"(list|report|propose|log|record)[^.\n]{0,60}"
    r"(before|instead of|rather than)[^.\n]{0,40}(delet|remov|destroy|purg)|"
    r"irreversible[^.\n]{0,80}(stop|ask|flag|do not|halt|defer|skip)|"
    r"safe(ly)? (stop|halt|abort|fallback)|"
    r"(backup|back up|archive|snapshot|tag)[^.\n]{0,60}"
    r"(before|prior to|first)|"
    r"recoverable|(can|could) be (restored|recovered|undone)|"
    r"when in doubt[^.\n]{0,40}(skip|leave|keep|do not))\b",
    re.I,
)


def result(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": str(evidence)[:400]}


def first_match(regex, text):
    m = regex.search(text)
    return m.group(0)[:120] if m else None


# A named CI job/workflow/pipeline whose green status is the gate is a runnable
# pass/fail oracle too (pilot calibration: "`wheel-build` passes on the PR branch").
JOB_GATE_RE = re.compile(
    r"`[^`\n]+`[^.\n]{0,40}\b(job|workflow|pipeline|check|run)s?\b"
    r"[^.\n]{0,30}(pass(es)?|green|succeed)|"
    r"\b(job|workflow|pipeline)\b[^.\n]{0,30}(must pass|passes|is green|succeeds)",
    re.I,
)

HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.M)
GATE_HEADING_RE = re.compile(
    r"(success criteri|acceptance|definition of done|verification|"
    r"completion|correctness gate|done when)", re.I)


def gate_sections(text):
    """Bodies of markdown sections whose heading is gate-flavored."""
    sections, current, keep = [], [], False
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            if keep and current:
                sections.append("\n".join(current))
            keep = bool(GATE_HEADING_RE.search(m.group(1)))
            current = []
        elif keep:
            current.append(line)
    if keep and current:
        sections.append("\n".join(current))
    return sections


def check_oracle(text, oracle_kind):
    """A concrete runnable check named in gate context: a block containing both
    a command-like token and completion-gate language; a gate-flavored heading's
    section counts as gate context for everything inside it (checklist briefs
    also accept a named checkable procedure in gate context)."""
    def has_cmd(chunk):
        return (INLINE_CMD_RE.search(chunk) or FENCE_CMD_RE.search(chunk)
                or BARE_CMD_RE.search(chunk) or JOB_GATE_RE.search(chunk))

    for b in blocks(text):
        if has_cmd(b) and GATE_LANG_RE.search(b):
            return True, "command+gate block: %r" % b[:160]
        if oracle_kind == "checklist" and GATE_LANG_RE.search(b) \
                and CHECKLIST_ORACLE_RE.search(b):
            return True, "checklist+gate block: %r" % b[:160]
    for s in gate_sections(text):
        if has_cmd(s):
            return True, "command under gate heading: %r" % s[:160]
        if oracle_kind == "checklist" and CHECKLIST_ORACLE_RE.search(s):
            return True, "checklist under gate heading: %r" % s[:160]
    return False, "no block pairs a runnable command%s with completion-gate language" % (
        " or checkable procedure" if oracle_kind == "checklist" else ""
    )


PROFILE_CHECKS = {
    "BUILD": [
        ("build_negative_cases_required",
         lambda t: NEGATIVE_CASE_RE.search(t),
         "requires testing negative/invalid/edge cases"),
    ],
    "OPTIMIZATION": [
        ("opt_fresh_baseline_required",
         lambda t: BASELINE_FRESH_RE.search(t),
         "requires establishing a fresh/current baseline measurement"),
        ("opt_regression_floor_required",
         lambda t: REGRESSION_FLOOR_RE.search(t),
         "states a no-regression floor"),
        ("opt_noise_handling_required",
         lambda t: NOISE_RE.search(t),
         "handles measurement noise/variance (multiple runs, median, band)"),
    ],
    "RESEARCH": [
        ("research_refutation_required",
         lambda t: HYPOTHESIS_RE.search(t) and REFUTE_RE.search(t),
         "hypothesis vocabulary plus explicit refute/rule-out condition"),
    ],
    "DECISION": [
        ("decision_criteria_first_required",
         lambda t: CRITERIA_FIRST_RE.search(t),
         "criteria/rubric fixed before scoring/evaluation"),
    ],
    "AUTHORING": [
        ("authoring_sourced_claims_required",
         lambda t: SOURCED_CLAIMS_RE.search(t),
         "claims/procedures traced to sources or fact-checked"),
    ],
    "REPAIR": [
        ("repair_reproduce_first_required",
         lambda t: REPRO_FIRST_RE.search(t),
         "reproduce the defect before fixing"),
        ("repair_regression_check_required",
         lambda t: REGRESSION_CHECK_RE.search(t),
         "checks for adjacent regressions"),
    ],
}


def grade(brief, text):
    results = []
    flags = brief.get("flags", [])
    tiny = "tiny" in flags
    nonblank = [l for l in text.splitlines() if l.strip()]
    words = len(text.split())

    # hygiene
    slots = SLOT_RE.findall(text)
    results.append(result("no_unresolved_slots", not slots,
                          "unresolved: %r" % slots[:5] if slots else "none"))
    notes = BUILDER_NOTE_RE.findall(text)
    results.append(result("no_builder_notes", not notes,
                          "leaked BUILDER notes: %d" % len(notes) if notes else "none"))

    mode_re = UNATTENDED_RE if brief["mode"] == "unattended" else INTERACTIVE_RE
    m = first_match(mode_re, text)
    results.append(result("mode_concept_present", m,
                          m or "no %s-mode handling language" % brief["mode"]))

    m = first_match(SCOPE_RE, text)
    results.append(result("scope_coverage", m, m or "no scope/out-of-scope statement"))

    m = first_match(HONEST_FAILURE_RE, text)
    results.append(result("honest_failure_path", m,
                          m or "no honest failure/inconclusive reporting path"))

    # mechanical forcing
    ok, ev = check_oracle(text, brief.get("oracle_kind", "command"))
    results.append(result("names_runnable_oracle", ok, ev))

    m = first_match(VERIFIER_RE, text)
    results.append(result("names_refuting_verifier", m,
                          m or "no fresh-context/adversarial doer!=grader verification step"))

    # profile knobs
    profile = brief.get("expected_profile")
    if profile:
        for part in profile.split("+"):
            for name, fn, desc in PROFILE_CHECKS[part]:
                hit = fn(text)
                ev = hit.group(0)[:120] if hasattr(hit, "group") else (
                    first_match_from(hit) if hit else None)
                results.append(result(name, bool(hit),
                                      (ev or "found") if hit else "missing: " + desc))

    if not tiny:
        m = first_match(PREREG_RE, text)
        results.append(result("prereg_before_work", m,
                              m or "no expected-outcome/prediction written before acting"))

    limit = SCALE_WORD_LIMITS[brief["scale"]]
    results.append(result("proportionate_to_scale", words <= limit,
                          "%d words vs %s limit %d (%d non-blank lines, logged secondary)"
                          % (words, brief["scale"], limit, len(nonblank))))

    if "destructive" in flags:
        m = first_match(AUTHORITY_RE, text)
        results.append(result("authority_boundary", m,
                              m or "no destructive-action guard/authorization/safe-stop"))
    return results


def first_match_from(hit):
    try:
        return hit.group(0)[:120]
    except Exception:
        return "found"


def load_brief(brief_id):
    data = json.loads(EVALS_JSON.read_text())
    for b in data["tracks"]["construction"]["briefs"]:
        if str(b["id"]) == str(brief_id) or b["slug"] == brief_id:
            return b
    raise SystemExit("unknown brief: %s" % brief_id)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    brief = load_brief(sys.argv[1])
    text = Path(sys.argv[2]).read_text(encoding="utf-8")
    results = grade(brief, text)
    json.dump(results, sys.stdout, indent=1)
    print()
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()

# Task: Rename `get_user_info` to `fetch_user_profile` across the repository

## Background and motivation

The function `get_user_info` has been with us since the first prototype of the account service, and its name has aged badly. It no longer returns a loose bag of "info": it returns a fully validated profile object with contact details, preference flags, notification settings, and the audit metadata the compliance team asked for last quarter. Half the new engineers who join the team read the name and assume it performs a cheap key lookup, when in reality it hydrates a complete profile aggregate. The platform working group agreed in the last API review that the name should become `fetch_user_profile`, which correctly signals both the remote fetch semantics and the shape of the returned object. Your job is to carry out that rename completely, mechanically, and safely across the whole Python repository, so that no trace of the old name survives anywhere it could mislead a reader or break a caller.

## What the rename must cover

Update the definition itself, every import of the function whether direct or aliased, every plain call site in application code, every call site in the test suite, every docstring or comment that refers to the function by name, and every string-based reference. The string-based category deserves special attention because it will not show up in a syntactic rename: mock patch targets such as `unittest.mock.patch("accounts.service.get_user_info")`, getattr lookups that build the attribute name dynamically, dispatch tables keyed by function name, and fixture files that mention the callable by its dotted path. Sweep configuration files and developer documentation in the repository as well, since several onboarding documents walk through example sessions that call the function by its old name. If an alias needs to remain temporarily for an external consumer, that is a decision I want to make, not you.

## Interaction

I am at my desk while you work. If you find a dynamic usage that cannot be renamed with confidence — a serialized reference in stored data, a string built at runtime from fragments, or anything that looks like an external system might depend on the old name — ask me before deciding what to do with it. I would much rather answer three small questions during the afternoon than discover a broken integration in the morning. When you ask, show me the exact line and file so I can make the call quickly.

## Scope discipline

Only change what the rename actually requires. Do not refactor surrounding code, do not reformat files that your editor happens to open, do not reorder imports beyond what the rename forces, and do not rename any other symbol however tempting it looks while you are in there. A reviewer should be able to read the diff and see one single, boring, mechanical change repeated many times, with nothing else mixed in. Every unrelated hunk in the diff makes the review slower and the revert story worse, so keep the change set surgical.

## Working method

Do the mechanical pass first with a project-wide search, then walk the results file by file rather than trusting a single global replace, because the old name appears inside at least one longer identifier (`get_user_info_cached`) that must be handled deliberately rather than clobbered by substring replacement. Take the test suite as your map: the tests reference the function through more paths than the application code does, including the patch targets mentioned above, and each one you update is one fewer surprise at the end.

## Completion gate

The rename is not done until `python -m pytest` passes with zero failures on the full suite and a whole-tree search for the string `get_user_info` comes back empty everywhere except the changelog entry you add. Run both checks at the very end, after your last edit, not midway through the work, and paste the final outputs into your summary so I can see them.

## Independent check

When you believe the work is complete, have a fresh session that did not make any of the edits go hunting on its own: its single mandate is to prove the rename incomplete or harmful, by searching for missed call sites, shadowed imports, stale patch targets, and any behavioral difference between the old and new entry points. Whatever it finds, fix, and then let it look once more.

## Honest outcome

If you cannot safely update every reference — because a usage is dynamic, serialized, or owned by something outside this repository — say so explicitly in your summary, list each leftover with its file, line, and the reason it was left, and propose what should happen to it. Do not hide a partial rename behind a green test suite, and do not quietly leave an alias in place without telling me.

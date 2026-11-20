# Task: Rename `get_user_info` to `fetch_user_profile`

Rename `get_user_info` to `fetch_user_profile` across the repo — definition, imports, call sites, tests, docstrings, and string references such as mock patch targets.

For orientation: the test suite lives under `tests/` and runs with `python -m pytest`; there is also `scripts/dev_shell.sh` if you want a preconfigured environment. Use whatever is convenient while exploring the codebase.

I am around while you work — if a rename target looks risky, ask me first.

Keep the diff minimal: only touch lines the rename requires, and do not reformat anything nearby.

Look over the result carefully when you finish, then have a fresh session that did not make the edits search for missed call sites and argue that the rename is incomplete.

If you cannot safely update a call site, say so plainly in your summary and list what you skipped and why.

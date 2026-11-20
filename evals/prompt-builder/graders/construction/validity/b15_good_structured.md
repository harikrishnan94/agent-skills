# Task: Rename `get_user_info` to `fetch_user_profile`

Rename the function `get_user_info` to `fetch_user_profile` across the repo and update every call site: definition, imports, calls, tests, docstrings that reference the name, and string-based references such as mock patch targets and getattr lookups.

## Interaction

I am around — if you find a dynamic usage that cannot be safely renamed (for example a serialized reference or something an external consumer might depend on), ask me before deciding.

## Scope

Only change what the rename requires. Do not refactor surrounding code, reformat files, or rename anything else while you are in there.

## Completion gate

The rename is not done until `python -m pytest` passes with zero failures and a whole-tree search for `get_user_info` comes back empty outside the changelog.

## Independent check

When you believe it is complete, have a fresh session that did not make the edits try to prove the rename incomplete or harmful — hunt for missed call sites, shadowed imports, and string references.

## Honest outcome

If you cannot safely update every call site, say so explicitly in your summary and list the leftovers with reasons — do not hide a partial rename behind a green suite.

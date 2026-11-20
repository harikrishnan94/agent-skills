Rename the Python function get_user_info to fetch_user_profile everywhere in the repo — definition, imports, call sites, tests, docstrings, and any place the name appears as a string (mock patch targets, getattr lookups).

I am around while you work: if a usage looks risky to rename — say something outside our repo might depend on it — ask me first.

Keep the change minimal: only touch lines the rename actually requires, and do not reformat or refactor anything nearby.

Before you call it done, run python -m pytest and it must pass clean, and sweep the whole tree for the old name to make sure nothing is left.

Then have a completely fresh session that did not do the editing go looking for anything you missed — its one job is to prove the rename is incomplete.

If you cannot rename a spot safely, do not quietly skip it — say so plainly in your summary and list exactly what you left and why.

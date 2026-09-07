#!/usr/bin/env python3
"""Stand-in for `gh api` in tests: replays scripted responses per endpoint.

`FAKE_GH_DIR/responses.json` maps an endpoint (the path after `repos/OWNER/REPO/`,
query string dropped) to a list of responses; the n-th call gets the n-th entry
and later calls repeat the last one. `{"fail": "message"}` prints the message to
stderr and exits 1, as `gh` does on an HTTP error.
"""

import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def main():
    args = sys.argv[1:]
    endpoint = next(arg for arg in args if arg.startswith("repos/"))
    key = urlsplit(endpoint).path.split("/", 3)[3]
    root = Path(os.environ["FAKE_GH_DIR"])
    responses = json.loads((root / "responses.json").read_text())[key]
    counter = root / "calls" / key.replace("/", "_")
    counter.parent.mkdir(exist_ok=True)
    calls = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(calls + 1))
    response = responses[min(calls, len(responses) - 1)]
    if isinstance(response, dict) and "fail" in response:
        print(response["fail"], file=sys.stderr)
        sys.exit(1)
    if "--paginate" in args:
        response = [response]
    print(json.dumps(response))


if __name__ == "__main__":
    main()

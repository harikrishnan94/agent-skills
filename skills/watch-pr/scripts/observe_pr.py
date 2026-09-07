#!/usr/bin/env python3
"""Retain complete GitHub observations without deciding whether a PR is done."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit


SCHEMA = 2
PASSING_CONCLUSIONS = {"success", "skipped", "neutral"}
LEVELS = {"checks": "job", "workflows": "run", "statuses": "status"}
MERGEABILITY_POLLS = 5
MERGEABILITY_WAIT = 2
LOCK_WAIT = 60
MAX_CONSECUTIVE_ERRORS = 5
MAX_BACKOFF = 900


class ObservationChanged(ValueError):
    """The PR or a paginated listing moved while it was being read."""


class ObserverBusy(Exception):
    """Another watcher owns this state directory."""


def now():
    return datetime.now(timezone.utc).isoformat()


def github(host, endpoint, paginate=False):
    command = ["gh", "api", "--hostname", host, "--method", "GET", endpoint]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def paginated(host, endpoint, key=None):
    pages = github(host, endpoint, paginate=True)
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"Missing pagination response: {endpoint}")
    rows = []
    for page in pages:
        items = page[key] if key else page
        if not isinstance(items, list):
            raise ValueError(f"Expected an array: {endpoint}")
        rows.extend(items)
    if key and "total_count" in pages[0] and len(rows) != pages[0]["total_count"]:
        raise ObservationChanged(f"Listing changed while paginating: {endpoint}")
    return sorted(rows, key=lambda row: row["id"])


def pr_metadata(pr):
    data = {key: pr[key] for key in (
        "html_url", "number", "state", "merged", "draft", "title", "body",
        "mergeable", "mergeable_state", "updated_at",
    )}
    for side in ("head", "base"):
        ref = pr[side]
        data[side] = {"sha": ref["sha"], "ref": ref["ref"],
                      "repo": ref["repo"]["full_name"] if ref["repo"] else None}
    data["test_merge_sha"] = (
        pr["merge_commit_sha"]
        if pr["state"] == "open" and pr["mergeable"] is True else None
    )
    data["labels"] = sorted(label["name"] for label in pr["labels"])
    data["requested_reviewers"] = sorted(user["login"] for user in pr["requested_reviewers"])
    data["requested_teams"] = sorted(team["slug"] for team in pr["requested_teams"])
    return data


def identity(pr):
    """The fields that decide what an observation collects."""
    return pr["state"], pr["head"]["sha"]


def settled_pr(host, endpoint):
    """GitHub computes mergeability lazily; the first read of a cold PR says null."""
    for _ in range(MERGEABILITY_POLLS - 1):
        pr = pr_metadata(github(host, endpoint))
        if pr["state"] != "open" or pr["mergeable"] is not None:
            return pr
        time.sleep(MERGEABILITY_WAIT)
    return pr_metadata(github(host, endpoint))


def observe(pr_url):
    url = urlsplit(pr_url)
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?", url.path)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.port or url.query or not match):
        raise ValueError("Expected an HTTPS GitHub PR URL: https://HOST/OWNER/REPO/pull/NUMBER")
    owner, repo, number = match.groups()
    if owner in (".", "..") or repo in (".", ".."):
        raise ValueError("Invalid repository name")
    host = url.hostname
    root = f"repos/{owner}/{repo}"
    endpoint = f"{root}/pulls/{number}"
    pr = settled_pr(host, endpoint)
    head = pr["head"]["sha"]
    # CI attaches to the head commit; GitHub's test-merge commit never carries any.
    sources = {
        "pr": pr,
        "discussion": paginated(host, f"{root}/issues/{number}/comments?per_page=100"),
        "review_comments": paginated(host, f"{endpoint}/comments?per_page=100"),
        "reviews": paginated(host, f"{endpoint}/reviews?per_page=100"),
        f"checks:{head}": paginated(
            host, f"{root}/commits/{head}/check-runs?filter=latest&per_page=100", "check_runs"),
        f"statuses:{head}": paginated(host, f"{root}/commits/{head}/status?per_page=100", "statuses"),
        f"workflows:{head}": paginated(
            host, f"{root}/actions/runs?head_sha={head}&per_page=100", "workflow_runs"),
    }
    if identity(pr_metadata(github(host, endpoint))) != identity(pr):
        raise ObservationChanged("PR head or state changed during collection; repeat the observation")
    return sources


def observe_settled(pr_url, attempts=3):
    """A busy PR can move during one collection; repeat before giving up."""
    for remaining in reversed(range(attempts)):
        try:
            return observe(pr_url)
        except ObservationChanged:
            if not remaining:
                raise


def summarize(sources):
    pr = sources["pr"]
    rows = []
    for source, items in sources.items():
        kind = source.split(":", 1)[0]
        if kind not in LEVELS:
            continue
        for row in items:
            if kind == "statuses":
                outcome, completed = row["state"], row["state"] != "pending"
                name, link = row["context"], row["target_url"]
            else:
                outcome = row["conclusion"]
                completed = row["status"] == "completed" and outcome is not None
                name, link = row["name"], row["html_url"]
            rows.append({"source": source, "level": LEVELS[kind], "id": row["id"], "name": name,
                         "outcome": outcome, "url": link, "completed": completed})
    if any(row["level"] == "job" for row in rows):
        # A workflow run only aggregates its jobs, and those are already check runs.
        rows = [row for row in rows if row["level"] != "run"]
    terminal = bool(rows) and all(row["completed"] for row in rows)
    finished = [{key: value for key, value in row.items() if key != "completed"}
                for row in rows if row["completed"]]
    return {"state": pr["state"], "merged": pr["merged"], "head": pr["head"]["sha"],
            "base": pr["base"]["sha"], "mergeable": pr["mergeable"],
            "mergeable_state": pr["mergeable_state"], "github_ci_rows": len(rows),
            "github_ci_terminal": terminal,
            "failures": [row for row in finished
                         if row["outcome"] not in PASSING_CONCLUSIONS | {"action_required"}],
            "action_required": [row for row in finished if row["outcome"] == "action_required"]}


def durable(handle, text):
    handle.write(text)
    handle.flush()
    os.fsync(handle.fileno())


def write_once(path, text):
    """Content-addressed: a file that already exists holds exactly these bytes."""
    if not path.exists():
        with path.open("x") as output:
            durable(output, text)


def append_event(state_dir, event):
    with (state_dir / "events.jsonl").open("a") as output:
        durable(output, json.dumps(event) + "\n")


def replace_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as output:
        durable(output, json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def record(state_dir, sources):
    summary = summarize(sources)
    latest_path = state_dir / "latest.json"
    previous = json.loads(latest_path.read_text()) if latest_path.exists() else None
    pr_url = sources["pr"]["html_url"]
    if previous and (previous["schema"] != SCHEMA or previous["pr_url"] != pr_url):
        raise ValueError("State directory belongs to a different PR or schema")
    blobs = {key: json.dumps(value, sort_keys=True, separators=(",", ":"))
             for key, value in sources.items()}
    hashes = {key: hashlib.sha256(blob.encode()).hexdigest() for key, blob in blobs.items()}
    previous_hashes = previous["source_hashes"] if previous else {}
    changed = sorted(key for key in hashes.keys() | previous_hashes.keys()
                     if hashes.get(key) != previous_hashes.get(key))
    # The same content always gets the same id, so a replayed event is recognizable.
    snapshot_id = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    observed_at = now()
    blob_dir = state_dir / "sources"
    blob_dir.mkdir(exist_ok=True)
    for key, digest in hashes.items():
        write_once(blob_dir / f"{digest}.json", blobs[key] + "\n")
    if changed:
        # Persist the event before advancing the cursor; interruption may replay, never erase it.
        append_event(state_dir, {"event": "changed", "observed_at": observed_at,
                                 "snapshot_id": snapshot_id, "changed": changed, "sources": hashes})
    replace_json(latest_path, {"schema": SCHEMA, "pr_url": pr_url, "observed_at": observed_at,
                               "snapshot_id": snapshot_id, "source_hashes": hashes})
    return {"event": "changed" if changed else "unchanged", "changed": changed,
            "snapshot_id": snapshot_id,
            "sources": {key: str(blob_dir / f"{digest}.json") for key, digest in hashes.items()},
            **summary}


def acquire(lock):
    """A one-shot read may overlap a watcher's poll; wait for it, then give up."""
    for _ in range(LOCK_WAIT):
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            time.sleep(1)
    raise ObserverBusy(lock.name)


def describe(error):
    return error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr_url")
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    state_dir = args.state_dir.resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    consecutive_errors = 0
    with (state_dir / "observer.lock").open("a") as lock, \
            (state_dir / "watch.lock").open("a") as watch_lock:
        if args.watch:
            try:
                fcntl.flock(watch_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ObserverBusy(watch_lock.name) from None
        while True:
            acquire(lock)
            try:
                result = record(state_dir, observe_settled(args.pr_url))
            except (subprocess.SubprocessError, ObservationChanged) as error:
                if not args.watch:
                    raise
                consecutive_errors += 1
                event = {"event": "observation_error", "observed_at": now(), "error": describe(error)}
                append_event(state_dir, event)
                print(json.dumps(event), file=sys.stderr, flush=True)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    raise
                result = None
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
            if result is None:
                time.sleep(min(args.interval * consecutive_errors, MAX_BACKOFF))
                continue
            consecutive_errors = 0
            if result["event"] == "changed" or not args.watch:
                print(json.dumps(result), flush=True)
            if not args.watch or result["state"] == "closed":
                return
            time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except ObserverBusy as error:
        print(json.dumps({"event": "observer_busy", "lock": str(error)}), file=sys.stderr)
        sys.exit(3)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"event": "observation_error", "error": describe(error)}), file=sys.stderr)
        sys.exit(1)

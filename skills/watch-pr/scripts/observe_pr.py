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
import tempfile
import time
from urllib.parse import urlsplit
import uuid


TERMINAL_CONCLUSIONS = {
    "success", "failure", "neutral", "cancelled", "skipped", "timed_out",
    "action_required", "stale", "startup_failure",
}


class ObservationChanged(ValueError):
    """PR metadata moved while its sources were being collected."""


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
        raise ValueError(f"Incomplete or changing pagination: {endpoint}")
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
    pr = pr_metadata(github(host, endpoint))
    sources = {"pr": pr}
    if pr["state"] == "open":
        sources["discussion"] = paginated(host, f"{root}/issues/{number}/comments?per_page=100")
        sources["review_comments"] = paginated(host, f"{endpoint}/comments?per_page=100")
        sources["reviews"] = paginated(host, f"{endpoint}/reviews?per_page=100")
        revisions = {pr["head"]["sha"], pr["test_merge_sha"]} - {None}
        for sha in sorted(revisions):
            sources[f"checks:{sha}"] = paginated(
                host, f"{root}/commits/{sha}/check-runs?filter=latest&per_page=100", "check_runs")
            sources[f"statuses:{sha}"] = paginated(
                host, f"{root}/commits/{sha}/status?per_page=100", "statuses")
            sources[f"workflows:{sha}"] = paginated(
                host, f"{root}/actions/runs?head_sha={sha}&per_page=100", "workflow_runs")
    if pr_metadata(github(host, endpoint)) != pr:
        raise ObservationChanged("PR changed during collection; repeat the observation")
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
    terminal = []
    failures = []
    for source, rows in sources.items():
        kind = source.split(":", 1)[0]
        if kind not in ("checks", "statuses", "workflows"):
            continue
        for row in rows:
            if kind == "statuses":
                outcome = row["state"]
                terminal.append(outcome in {"success", "failure", "error"})
                failed = outcome in {"failure", "error"}
                name, link = row["context"], row["target_url"]
            else:
                outcome = row["conclusion"]
                terminal.append(row["status"] == "completed" and outcome in TERMINAL_CONCLUSIONS)
                failed = outcome in TERMINAL_CONCLUSIONS - {"success", "skipped", "neutral"}
                name, link = row["name"], row["html_url"]
            if failed:
                failures.append({"source": source, "id": row["id"], "name": name,
                                 "outcome": outcome, "url": link})
    return {"state": pr["state"], "merged": pr["merged"], "head": pr["head"]["sha"],
            "base": pr["base"]["sha"], "mergeable": pr["mergeable"],
            "mergeable_state": pr["mergeable_state"], "github_ci_rows": len(terminal),
            "github_ci_terminal": bool(terminal) and all(terminal), "failures": failures}


def record(state_dir, sources):
    summary = summarize(sources)
    latest_path = state_dir / "latest.json"
    previous = json.loads(latest_path.read_text()) if latest_path.exists() else None
    pr_url = sources["pr"]["html_url"]
    if previous and (previous["schema"] != 1 or previous["pr_url"] != pr_url):
        raise ValueError("State directory belongs to a different PR or schema")
    hashes = {key: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
              for key, value in sources.items()}
    previous_hashes = previous["source_hashes"] if previous else {}
    changed = sorted(key for key in hashes.keys() | previous_hashes.keys()
                     if hashes.get(key) != previous_hashes.get(key))
    observed_at = datetime.now(timezone.utc).isoformat()
    if changed:
        snapshot_id = uuid.uuid4().hex
        snapshot_dir = state_dir / "snapshots"
        snapshot_dir.mkdir(exist_ok=True)
        snapshot_path = snapshot_dir / f"{snapshot_id}.json"
        with snapshot_path.open("x") as output:
            json.dump({"observed_at": observed_at, "sources": sources}, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        event = {"observed_at": observed_at, "snapshot_id": snapshot_id,
                 "changed": changed, "snapshot": str(snapshot_path)}
        # Persist the event before advancing the cursor; interruption may replay, never erase it.
        with (state_dir / "events.jsonl").open("a") as output:
            output.write(json.dumps(event) + "\n")
            output.flush()
            os.fsync(output.fileno())
    else:
        snapshot_id = previous["snapshot_id"]
        snapshot_path = state_dir / "snapshots" / f"{snapshot_id}.json"
    latest = {"schema": 1, "pr_url": pr_url, "observed_at": observed_at,
              "snapshot_id": snapshot_id, "source_hashes": hashes}
    with tempfile.NamedTemporaryFile(mode="w", dir=state_dir, delete=False) as output:
        temporary_path = Path(output.name)
        try:
            json.dump(latest, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
            temporary_path.replace(latest_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    return {"event": "changed" if changed else "unchanged", "changed": changed,
            "snapshot_id": snapshot_id, "snapshot": str(snapshot_path),
            **summary}


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
    with (state_dir / "observer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            result = record(state_dir, observe_settled(args.pr_url))
            if result["event"] == "changed" or not args.watch:
                print(json.dumps(result), flush=True)
            if not args.watch or result["state"] == "closed":
                return
            time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(json.dumps({"event": "observation_error", "error": detail}), file=sys.stderr)
        sys.exit(1)

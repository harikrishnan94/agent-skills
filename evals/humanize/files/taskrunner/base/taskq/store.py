import json
import os
import time

Q_PATH = os.environ.get("TASKQ_PATH", os.path.expanduser("~/.taskq.json"))


def _atomic_write(path, recs):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(recs, f)
        f.flush()
        # fsync before rename: crash during ack must not lose the queue
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def add(title, due_h=24, path=Q_PATH):
    recs = _load(path)
    nid = max((r["id"] for r in recs), default=0) + 1
    # ts stored as int epoch, not iso — ls sorts numerically
    ts = int(time.time())
    rec = {"id": nid, "title": title, "ts": ts, "due": ts + due_h * 3600, "done": False}
    recs.append(rec)
    _atomic_write(path, recs)
    return rec


def ls(path=Q_PATH):
    return sorted(_load(path), key=lambda r: r.get("ts", 0))


def done(tid, path=Q_PATH):
    recs = _load(path)
    for r in recs:
        if r["id"] == tid:
            r["done"] = True
            _atomic_write(path, recs)
            return r
    return None

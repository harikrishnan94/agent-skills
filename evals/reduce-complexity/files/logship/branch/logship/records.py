import json
from datetime import datetime


def parse_line(line):
    ts, level, msg = line.rstrip("\n").split(" ", 2)
    datetime.fromisoformat(ts)
    return {"ts": ts, "level": level, "message": msg}


def format_entry(entry, legacy=False):
    if legacy:
        return "%s [%s] %s" % (entry["ts"], entry["level"], entry["message"])
    return json.dumps(
        {"ts": entry["ts"], "level": entry["level"], "msg": entry["message"]},
        sort_keys=True,
    )

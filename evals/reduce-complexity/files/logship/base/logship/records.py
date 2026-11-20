from datetime import datetime


def parse_line(line):
    ts, level, msg = line.rstrip("\n").split(" ", 2)
    datetime.fromisoformat(ts)
    return {"ts": ts, "level": level, "message": msg}


def format_entry(entry):
    return "%s [%s] %s" % (entry["ts"], entry["level"], entry["message"])

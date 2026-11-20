from datetime import datetime, timezone


def parse_timestamp(s: str) -> float:
    """ISO-8601 to epoch seconds; feed timestamps use a trailing Z."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

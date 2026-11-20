import csv
import io
import json
from datetime import datetime, timezone

FIELDS = ["sku", "qty", "total_cents", "updated"]


def _parse_iso8601(s):
    # feed timestamps use a trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    parsed = datetime.fromisoformat(s)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _render_updated(value):
    if not value:
        return ""
    return "%d" % _parse_iso8601(value)


def export_csv(rows):
    cleaned = []
    for row in rows:
        if not row.get("sku"):
            continue
        qty = row.get("qty", 0)
        if qty < 0:
            qty = 0
        cleaned.append({**row, "qty": qty})
    cleaned.sort(key=lambda r: r["sku"])
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for row in cleaned:
        writer.writerow({
            "sku": row["sku"],
            "qty": row["qty"],
            "total_cents": row.get("total_cents", 0),
            "updated": _render_updated(row.get("updated")),
        })
    return buf.getvalue()


def export_json(rows):
    keep = []
    for entry in rows:
        if not entry.get("sku"):
            continue
        count = entry.get("qty", 0)
        if count < 0:
            count = 0
        keep.append({**entry, "qty": count})
    keep.sort(key=lambda e: e["sku"])
    out = []
    for entry in keep:
        out.append({
            "sku": entry["sku"],
            "qty": entry["qty"],
            "total_cents": entry.get("total_cents", 0),
            "updated": _render_updated(entry.get("updated")),
        })
    return json.dumps(out, indent=2)

"""Feed summary rendering."""

VENDOR = 2
PRICE = 4
QTY = 5


def render_summary(header, rows):
    """Render a plain-text summary of a parsed feed."""
    total_units = 0
    total_value = 0.0
    vendors = {}
    for row in rows:
        price = float(row[PRICE])
        qty = int(row[QTY])
        total_units += qty
        total_value += price * qty
        vendors[row[VENDOR]] = vendors.get(row[VENDOR], 0) + 1
    lines = [
        "Feed summary",
        "------------",
        "rows: %d" % len(rows),
        "units: %d" % total_units,
        "value: %.2f" % total_value,
        "vendors:",
    ]
    for vendor in sorted(vendors):
        lines.append("  %s: %d" % (vendor, vendors[vendor]))
    return "\n".join(lines)

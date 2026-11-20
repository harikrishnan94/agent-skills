"""Feed export for downstream consumers."""

import csv


def export_csv(header, rows, out_path):
    """Write the parsed feed back out as normalized CSV. Returns row count."""
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return len(rows)

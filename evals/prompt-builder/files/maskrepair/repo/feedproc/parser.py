"""Feed file parsing helpers."""


def parse_row(line):
    """Split one feed line into a list of field values."""
    fields = line.rstrip("\r\n").split(",")
    return [f.strip().strip('"') for f in fields]


def read_feed(path):
    """Read a feed file. Returns (header, rows)."""
    with open(path, encoding="utf-8") as fh:
        lines = [line for line in fh if line.strip()]
    if not lines:
        return [], []
    header = parse_row(lines[0])
    rows = [parse_row(line) for line in lines[1:]]
    return header, rows

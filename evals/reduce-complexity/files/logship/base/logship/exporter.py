from logship.records import format_entry, parse_line


def export_lines(lines, out):
    n = 0
    for line in lines:
        if not line.strip():
            continue
        out.write(format_entry(parse_line(line)) + "\n")
        n += 1
    return n

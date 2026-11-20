import sys

from logship.exporter import export_lines


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: logship <logfile>", file=sys.stderr)
        return 2
    with open(argv[0]) as f:
        n = export_lines(f, sys.stdout)
    print("exported %d entries" % n, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

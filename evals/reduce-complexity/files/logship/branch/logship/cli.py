import sys

from logship.exporter import export_batches, export_lines


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    batch = False
    if argv and argv[0] == "--batch":
        batch = True
        argv = argv[1:]
    if len(argv) != 1:
        print("usage: logship [--batch] <logfile>", file=sys.stderr)
        return 2
    with open(argv[0]) as f:
        run = export_batches if batch else export_lines
        n = run(f, sys.stdout)
    print("exported %d entries" % n, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

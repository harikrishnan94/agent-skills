#!/usr/bin/env python3
"""Command-line interface for the feed processor."""

import argparse

from feedproc.export import export_csv
from feedproc.parser import read_feed
from feedproc.summary import render_summary


def main(argv=None):
    parser = argparse.ArgumentParser(prog="feedproc")
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="print a summary of a feed file")
    p_summary.add_argument("feed")

    p_export = sub.add_parser("export", help="export a feed file as normalized CSV")
    p_export.add_argument("feed")
    p_export.add_argument("out")

    args = parser.parse_args(argv)
    header, rows = read_feed(args.feed)
    if args.command == "summary":
        print(render_summary(header, rows))
    else:
        count = export_csv(header, rows, args.out)
        print("wrote %d rows to %s" % (count, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

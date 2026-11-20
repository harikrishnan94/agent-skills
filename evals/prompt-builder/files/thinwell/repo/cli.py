#!/usr/bin/env python3
"""Command-line interface for the document store."""
import argparse
import sys

from store import Store


def main(argv=None):
    parser = argparse.ArgumentParser(prog="docstore")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_put = sub.add_parser("put", help="store a value under a key")
    p_put.add_argument("file")
    p_put.add_argument("key")
    p_put.add_argument("value")

    p_get = sub.add_parser("get", help="print the value stored under a key")
    p_get.add_argument("file")
    p_get.add_argument("key")

    p_list = sub.add_parser("list", help="print all keys, one per line")
    p_list.add_argument("file")

    args = parser.parse_args(argv)
    store = Store(args.file)
    if args.cmd == "put":
        store.put(args.key, args.value)
    elif args.cmd == "get":
        try:
            print(store.get(args.key))
        except KeyError:
            print("no such key: %s" % args.key, file=sys.stderr)
            return 1
    elif args.cmd == "list":
        for key in store.keys():
            print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())

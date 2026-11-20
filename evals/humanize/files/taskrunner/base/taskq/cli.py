import argparse

from taskq import fmt, store


def main(argv=None):
    p = argparse.ArgumentParser(prog="taskq")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add")
    sp.add_argument("title")
    sp.add_argument("--due-h", type=int, default=24)

    sub.add_parser("ls")

    sp = sub.add_parser("done")
    sp.add_argument("id", type=int)

    args = p.parse_args(argv)

    if args.cmd == "add":
        print(fmt.fmt_row(store.add(args.title, args.due_h)))
    elif args.cmd == "ls":
        for r in store.ls():
            print(fmt.fmt_row(r))
    elif args.cmd == "done":
        r = store.done(args.id)
        print(fmt.fmt_row(r) if r else "no such task")


if __name__ == "__main__":
    main()

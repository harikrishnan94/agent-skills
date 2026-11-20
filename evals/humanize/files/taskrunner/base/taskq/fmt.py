import time


def fmt_ts(ts):
    return time.strftime("%m-%d %H:%M", time.localtime(ts))


def fmt_row(rec):
    mark = "x" if rec["done"] else " "
    return "[%s] %3d %s (due %s)" % (mark, rec["id"], rec["title"], fmt_ts(rec["due"]))

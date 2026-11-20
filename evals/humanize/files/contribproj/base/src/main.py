import sys

from src.parser import parse


def main():
    with open(sys.argv[1]) as f:
        cfg = parse(f.read())
    for k in sorted(cfg):
        print("%s=%s" % (k, cfg[k]))


if __name__ == "__main__":
    main()

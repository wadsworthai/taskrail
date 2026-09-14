"""Command line: python3 -m wordstat FILE."""

import argparse
import sys

from . import stats


def main(argv=None):
    parser = argparse.ArgumentParser(prog="wordstat", description="Count the words in a text file.")
    parser.add_argument("file", help="the text file to read")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print(f"wordstat: cannot read {args.file}: {error.strerror}", file=sys.stderr)
        return 1
    for key, value in stats(text).items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

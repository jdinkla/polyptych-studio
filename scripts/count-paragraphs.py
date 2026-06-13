#!/usr/bin/env python3
"""Debug tool: show paragraph IDs as used by slide_timing.parse_paragraphs."""

import re
import sys


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <text-file>", file=sys.stderr)
        sys.exit(1)

    text = open(sys.argv[1]).read()
    blocks = re.split(r"\n\s*\n", text.strip())

    for i, block in enumerate(blocks, start=1):
        stripped = block.strip()
        if stripped:
            print(f"{i}: {stripped}\n")


if __name__ == "__main__":
    main()

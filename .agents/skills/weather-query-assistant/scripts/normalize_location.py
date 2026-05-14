#!/usr/bin/env python3
import re
import sys


def normalize_location(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"\s+", " ", value)
    value = value.replace(",", " ")
    value = re.sub(r"\s+", " ", value).strip()

    upper_special = {"jfk", "lax", "sfo", "lhr", "cdg", "hnd"}
    if value.lower() in upper_special:
        return value.upper()

    parts = []
    for token in value.split(" "):
        if len(token) <= 3 and token.isalpha() and token.isupper():
            parts.append(token)
        elif token.isalpha():
            parts.append(token.capitalize())
        else:
            parts.append(token)

    return "+".join(parts)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: normalize_location.py <location>")
        return 1

    print(normalize_location(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

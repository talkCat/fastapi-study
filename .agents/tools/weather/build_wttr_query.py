#!/usr/bin/env python3
import argparse

from normalize_location import normalize_location


MODE_TO_FORMAT = {
    "current": "3",
    "compact": "%l:+%c+%t+%h+%w",
    "full": "T",
}


def build_wttr_query(location: str, mode: str = "compact", units: str = "metric") -> str:
    normalized = normalize_location(location)
    format_part = MODE_TO_FORMAT[mode]
    units_suffix = "m" if units == "metric" else "u"
    return f"https://wttr.in/{normalized}?{units_suffix}&format={format_part}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a wttr.in query URL from a user-provided location.")
    parser.add_argument("location", help="Raw location input from the user")
    parser.add_argument("--mode", choices=sorted(MODE_TO_FORMAT.keys()), default="compact")
    parser.add_argument("--units", choices=["metric", "uscs"], default="metric")
    args = parser.parse_args()

    print(build_wttr_query(args.location, mode=args.mode, units=args.units))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
from build_open_meteo_query import build_open_meteo_query
from build_wttr_query import build_wttr_query
from normalize_location import normalize_location


def main() -> int:
    checks = [
        ("normalize beijing", normalize_location("beijing"), "Beijing"),
        ("normalize new york", normalize_location(" New   York "), "New+York"),
        ("normalize airport code", normalize_location("jfk"), "JFK"),
        (
            "build wttr current",
            build_wttr_query("beijing", mode="current"),
            "https://wttr.in/Beijing?m&format=3",
        ),
        (
            "build wttr compact uscs",
            build_wttr_query("jfk", mode="compact", units="uscs"),
            "https://wttr.in/JFK?u&format=%l:+%c+%t+%h+%w",
        ),
        (
            "build open-meteo beijing",
            build_open_meteo_query("beijing"),
            "https://api.open-meteo.com/v1/forecast?latitude=39.9042&longitude=116.4074&current_weather=true",
        ),
    ]

    failures = []
    for name, actual, expected in checks:
        ok = actual == expected
        print(f"[{'OK' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")
            failures.append(name)

    try:
        build_open_meteo_query("chengdu")
        print("[FAIL] unsupported fallback location should raise")
        failures.append("unsupported fallback location should raise")
    except ValueError:
        print("[OK] unsupported fallback location should raise")

    if failures:
        print(f"validation-failed: {len(failures)} checks failed")
        return 1

    print("validation-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

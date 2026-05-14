#!/usr/bin/env python3
from fetch_weather import fetch_weather


def main() -> int:
    failures = []

    def fake_wttr_get(url: str, timeout: float) -> tuple[int, str]:
        return 200, "Beijing: Sunny +25C 40% 9km/h"

    wttr_result = fetch_weather("beijing", http_get_func=fake_wttr_get)
    if wttr_result["ok"] and wttr_result["source"] == "wttr.in" and "Sunny" in wttr_result["summary"]:
        print("[OK] fetch weather primary path")
    else:
        print("[FAIL] fetch weather primary path")
        print(f"  actual: {wttr_result}")
        failures.append("fetch weather primary path")

    def fake_open_meteo_get(url: str, timeout: float) -> tuple[int, str]:
        return 200, '{"current_weather":{"temperature":21.5,"windspeed":8.0,"weathercode":2}}'

    open_meteo_result = fetch_weather(
        "beijing",
        source="open-meteo",
        http_get_func=fake_open_meteo_get,
    )
    if (
        open_meteo_result["ok"]
        and open_meteo_result["source"] == "Open-Meteo"
        and "partly cloudy" in open_meteo_result["summary"]
    ):
        print("[OK] fetch weather fallback path")
    else:
        print("[FAIL] fetch weather fallback path")
        print(f"  actual: {open_meteo_result}")
        failures.append("fetch weather fallback path")

    if failures:
        print(f"validation-failed: {len(failures)} checks failed")
        return 1

    print("validation-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


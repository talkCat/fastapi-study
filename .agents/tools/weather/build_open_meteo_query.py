#!/usr/bin/env python3
import argparse

from normalize_location import normalize_location


DEMO_COORDS = {
    "Beijing": (39.9042, 116.4074),
    "Shanghai": (31.2304, 121.4737),
    "London": (51.5072, -0.1276),
    "New+York": (40.7128, -74.0060),
    "JFK": (40.6413, -73.7781),
}


def build_open_meteo_query(location: str) -> str:
    normalized = normalize_location(location)
    if normalized not in DEMO_COORDS:
        supported = ", ".join(sorted(DEMO_COORDS))
        raise ValueError(
            f"Unsupported demo location: {normalized}. Supported demo locations: {supported}"
        )

    latitude, longitude = DEMO_COORDS[normalized]
    return (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}&current_weather=true"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an Open-Meteo fallback URL from a user-provided location."
    )
    parser.add_argument("location", help="Raw location input from the user")
    args = parser.parse_args()

    try:
        print(build_open_meteo_query(args.location))
    except ValueError as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


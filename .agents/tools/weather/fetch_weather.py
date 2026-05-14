#!/usr/bin/env python3
import argparse
import json
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from build_open_meteo_query import build_open_meteo_query
from build_wttr_query import build_wttr_query
from normalize_location import normalize_location

HttpGet = Callable[[str, float], tuple[int, str]]


WEATHER_CODE_LABELS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def http_get(url: str, timeout: float) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "fastapi-study-weather-tool/1.0"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def fetch_weather(
    location: str,
    source: str = "auto",
    units: str = "metric",
    timeout: float = 8.0,
    http_get_func: HttpGet | None = None,
) -> dict:
    normalized = normalize_location(location)
    getter = http_get_func or http_get

    if source not in {"auto", "wttr", "open-meteo"}:
        raise ValueError("source must be one of: auto, wttr, open-meteo")

    if source in {"auto", "wttr"}:
        wttr_url = build_wttr_query(location, mode="compact", units=units)
        try:
            status_code, body = getter(wttr_url, timeout)
            summary = " ".join(body.split())
            if status_code == 200 and summary:
                return {
                    "ok": True,
                    "source": "wttr.in",
                    "location": normalized,
                    "query_url": wttr_url,
                    "summary": summary,
                    "raw": body,
                }
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if source == "wttr":
                return {
                    "ok": False,
                    "source": "wttr.in",
                    "location": normalized,
                    "query_url": wttr_url,
                    "error": str(exc),
                }

    try:
        open_meteo_url = build_open_meteo_query(location)
        status_code, body = getter(open_meteo_url, timeout)
        payload = json.loads(body)
        current = payload.get("current_weather") or {}
        weather_code = current.get("weathercode")
        condition = WEATHER_CODE_LABELS.get(weather_code, f"weather code {weather_code}")
        temperature_unit = "C" if units == "metric" else "F"
        summary = (
            f"{normalized}: {condition}, "
            f"{current.get('temperature')} deg {temperature_unit}, "
            f"wind {current.get('windspeed')} km/h"
        )
        return {
            "ok": status_code == 200,
            "source": "Open-Meteo",
            "location": normalized,
            "query_url": open_meteo_url,
            "summary": summary,
            "current_weather": current,
        }
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "source": "Open-Meteo",
            "location": normalized,
            "query_url": locals().get("open_meteo_url"),
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch weather with wttr.in primary and Open-Meteo fallback.")
    parser.add_argument("location", help="Raw location input from the user")
    parser.add_argument("--source", choices=["auto", "wttr", "open-meteo"], default="auto")
    parser.add_argument("--units", choices=["metric", "uscs"], default="metric")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    result = fetch_weather(
        args.location,
        source=args.source,
        units=args.units,
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


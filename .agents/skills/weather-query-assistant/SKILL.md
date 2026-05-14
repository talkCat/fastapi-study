---
name: weather
description: Get current weather and forecasts (no API key required).
homepage: https://wttr.in/:help
metadata: {"nanobot":{"emoji":"🌤️","requires":{"bins":["curl"]}}}
---

# Weather

Use this skill when the user asks for current weather or a short forecast for a specific location.

## Workflow

1. Check whether the user gave a clear location.
2. If the location is missing or ambiguous, ask a short clarification question.
3. Normalize the location when the user input is noisy or inconsistently formatted.
4. Build a stable weather query string before calling the external service.
5. Use `wttr.in` as the primary source.
6. Use Open-Meteo as a fallback when JSON output or more programmatic structure is needed.
7. Answer concisely with practical details:
   - location
   - current condition or forecast summary
   - temperature
   - humidity or wind when relevant
   - rain risk when relevant
8. Do not guess when weather data is unavailable.

## References

- Read `references/weather_sources.md` for concrete `wttr.in` and Open-Meteo query patterns.

## Scripts

- Run `scripts/normalize_location.py "<user-location>"` when the location needs deterministic cleanup before querying weather sources.
- Run `scripts/build_wttr_query.py "<user-location>"` to generate a query-ready `wttr.in` URL after normalization.
- Run `scripts/build_open_meteo_query.py "<user-location>"` when the fallback path needs a JSON-friendly Open-Meteo URL.
- Run `scripts/validate_weather_skill.py` to do a quick validation pass over normalization, primary query building, and fallback query building.

## Related Tools

- Runtime tools live outside this Skill directory under `.agents/tools/weather/`.
- Use `.agents/tools/weather/fetch_weather.py "<user-location>"` when an agent or notebook needs a structured weather result.
- Use `.agents/tools/weather/validate_weather_tool.py` to validate the runtime tool paths.

## Style

- Prefer short, direct answers.
- Use the exact place name from the user when possible.
- Prefer `wttr.in` for human-readable responses.
- Prefer Open-Meteo when structured JSON is needed.
- If data is unavailable, say that clearly instead of guessing.
- Do not turn a simple weather answer into a travel or climate essay.

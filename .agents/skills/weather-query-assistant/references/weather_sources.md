# Weather Sources

This reference contains the concrete query patterns for the weather skill.

Use `wttr.in` as the primary source for concise, human-readable weather output.

Use Open-Meteo as the fallback when a structured JSON response is more useful.

## wttr.in

Quick one-liner:

```bash
curl -s "wttr.in/London?format=3"
# Output: London: ⛅️ +8°C
```

Compact format:

```bash
curl -s "wttr.in/London?format=%l:+%c+%t+%h+%w"
# Output: London: ⛅️ +8°C 71% ↙5km/h
```

Full forecast:

```bash
curl -s "wttr.in/London?T"
```

Format codes:

- `%c` condition
- `%t` temp
- `%h` humidity
- `%w` wind
- `%l` location
- `%m` moon

Tips:

- URL-encode spaces: `wttr.in/New+York`
- Airport codes: `wttr.in/JFK`
- Units: `?m` for metric, `?u` for USCS
- Today only: `?1`
- Current only: `?0`
- PNG output: `curl -s "wttr.in/Berlin.png" -o /tmp/weather.png`

## Open-Meteo

Use this when a structured JSON response is more useful than text.

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.12&current_weather=true"
```

Find coordinates for the city first, then query Open-Meteo. The response includes fields such as current temperature, wind speed, and weather code.

For this teaching repo, the scripted fallback path uses a small built-in coordinate map for a few demo locations instead of doing full geocoding.

Current demo locations supported by the scripted fallback:

- Beijing
- Shanghai
- London
- New York
- JFK

Docs:

- https://open-meteo.com/en/docs

---
name: weather-query-assistant
description: Help with weather questions. Use when the user wants current weather or a short weather outlook for a specific location, and keep the answer concise and practical.
---

# Weather Query Assistant

Use this skill when the user is asking about weather for a city, region, or specific location.

## Workflow

1. Check whether the user has already provided a clear location.
2. If the location is missing or ambiguous, ask a short clarification question.
3. Use the available weather capability or weather tool to get the forecast or current weather.
4. Answer with concise, practical details:
   - location
   - current condition or forecast summary
   - high / low temperature when available
   - rain or wind risk when relevant
5. Avoid turning a simple weather answer into a long travel or climate essay.

## Style

- Prefer short, direct answers.
- Use exact place names from the user when possible.
- If the weather data is unavailable, say that clearly instead of guessing.


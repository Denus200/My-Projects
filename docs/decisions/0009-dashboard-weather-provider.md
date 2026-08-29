# Decision 0009 — Dashboard Weather Provider

Date: 2026-08-27

Status: Accepted

## Context

The approved Dashboard Weather card initially used deterministic mock forecast data. It now needs real current and five-day weather for one explicitly configured location without coupling HTTP, Open-Meteo response fields, or WMO codes to Flet Presentation.

## Decision

- Use the Open-Meteo Forecast API without an API key for fixed Merefa coordinates `49.8211, 36.0567` and timezone `Europe/Kyiv`.
- Keep location metadata in one `WeatherConfig` value. Location search, GPS, and Settings remain out of scope.
- Keep a provider port in Application. `OpenMeteoWeatherProvider` owns HTTP, timeout, response validation, and WMO normalization; the Weather widget receives only normalized read models.
- Request current `temperature_2m`, `weather_code`, and `is_day`, plus five daily `weather_code`, `temperature_2m_max`, `temperature_2m_min`, and `temperature_2m_mean` values in Celsius.
- Use current temperature/code for today's card. Use daily mean, with max/min midpoint fallback, for future cards.
- Cache only the normalized successful result and UTC save time in `{database-stem}-weather-cache.json` beside the selected database. Production and demo caches therefore remain isolated.
- Render the cached snapshot synchronously. Refresh through the mounted Flet app in a background thread at startup and after a 30-minute freshness window; retry an unavailable first load after five minutes.
- Preserve stale cache on timeout, network failure, provider error, or malformed payload. When no cache exists, return a contained unavailable read model rather than surfacing a Python exception.

## Consequences

Overlord remains local-first for canonical planning data, but Dashboard Weather now has one narrow outbound dependency. SQLite schema and transactions are unchanged. Resize, maximize/restore, Sidebar changes, route reconstruction, and day-tab switching do not initiate network requests. Another provider can replace Open-Meteo without changing the approved widget.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from overlord.modules.weather.config import WeatherConfig
from overlord.modules.weather.read_models import ForecastDay, WeatherGroup, WeatherReadModel


OPEN_METEO_FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


class WeatherProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedWeatherCondition:
    condition_key: str
    visual_group: WeatherGroup


_WMO_CONDITIONS: dict[int, NormalizedWeatherCondition] = {
    0: NormalizedWeatherCondition("sunny", WeatherGroup.SUNNY),
    1: NormalizedWeatherCondition("mainly_clear", WeatherGroup.SUNNY),
    2: NormalizedWeatherCondition("partly_cloudy", WeatherGroup.CLOUDY),
    3: NormalizedWeatherCondition("overcast", WeatherGroup.CLOUDY),
    45: NormalizedWeatherCondition("fog", WeatherGroup.CLOUDY),
    48: NormalizedWeatherCondition("rime_fog", WeatherGroup.CLOUDY),
    51: NormalizedWeatherCondition("light_drizzle", WeatherGroup.RAINY),
    53: NormalizedWeatherCondition("drizzle", WeatherGroup.RAINY),
    55: NormalizedWeatherCondition("heavy_drizzle", WeatherGroup.RAINY),
    56: NormalizedWeatherCondition("freezing_drizzle", WeatherGroup.RAINY),
    57: NormalizedWeatherCondition("heavy_freezing_drizzle", WeatherGroup.RAINY),
    61: NormalizedWeatherCondition("light_rain", WeatherGroup.RAINY),
    63: NormalizedWeatherCondition("rain", WeatherGroup.RAINY),
    65: NormalizedWeatherCondition("heavy_rain", WeatherGroup.RAINY),
    66: NormalizedWeatherCondition("freezing_rain", WeatherGroup.RAINY),
    67: NormalizedWeatherCondition("heavy_freezing_rain", WeatherGroup.RAINY),
    71: NormalizedWeatherCondition("light_snow", WeatherGroup.SNOWY),
    73: NormalizedWeatherCondition("snowy", WeatherGroup.SNOWY),
    75: NormalizedWeatherCondition("heavy_snow", WeatherGroup.SNOWY),
    77: NormalizedWeatherCondition("snow_grains", WeatherGroup.SNOWY),
    80: NormalizedWeatherCondition("light_rain_showers", WeatherGroup.RAINY),
    81: NormalizedWeatherCondition("rain_showers", WeatherGroup.RAINY),
    82: NormalizedWeatherCondition("heavy_rain_showers", WeatherGroup.RAINY),
    85: NormalizedWeatherCondition("snow_showers", WeatherGroup.SNOWY),
    86: NormalizedWeatherCondition("heavy_snow_showers", WeatherGroup.SNOWY),
    95: NormalizedWeatherCondition("thunderstorm", WeatherGroup.RAINY),
    96: NormalizedWeatherCondition("thunderstorm_hail", WeatherGroup.RAINY),
    99: NormalizedWeatherCondition("heavy_thunderstorm_hail", WeatherGroup.RAINY),
}


def normalize_wmo_code(code: int) -> NormalizedWeatherCondition:
    try:
        return _WMO_CONDITIONS[int(code)]
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherProviderError(f"Unsupported Open-Meteo weather code: {code!r}") from error


class OpenMeteoWeatherProvider:
    def __init__(
        self,
        config: WeatherConfig,
        *,
        timeout_seconds: float = 8.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def forecast(self) -> WeatherReadModel:
        request = Request(
            f"{OPEN_METEO_FORECAST_ENDPOINT}?{urlencode(self._query())}",
            headers={"User-Agent": "Overlord/0.1 Weather"},
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise WeatherProviderError("Open-Meteo request failed.") from error
        return self._normalize(payload)

    def _query(self) -> dict[str, str | int | float]:
        return {
            "latitude": self._config.latitude,
            "longitude": self._config.longitude,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,temperature_2m_mean",
            "temperature_unit": "celsius",
            "timezone": self._config.timezone,
            "forecast_days": 5,
        }

    def _normalize(self, payload: object) -> WeatherReadModel:
        if not isinstance(payload, dict) or payload.get("error"):
            raise WeatherProviderError("Open-Meteo returned an invalid response.")
        current = payload.get("current")
        daily = payload.get("daily")
        if not isinstance(current, dict) or not isinstance(daily, dict):
            raise WeatherProviderError("Open-Meteo response is missing current or daily weather.")

        times = self._daily_values(daily, "time")
        codes = self._daily_values(daily, "weather_code")
        highs = self._daily_values(daily, "temperature_2m_max")
        lows = self._daily_values(daily, "temperature_2m_min")
        raw_means = daily.get("temperature_2m_mean")
        means = list(raw_means) if isinstance(raw_means, list) else []
        means.extend([None] * max(0, len(times) - len(means)))
        if min(len(times), len(codes), len(highs), len(lows)) < 5:
            raise WeatherProviderError("Open-Meteo returned fewer than five forecast days.")

        try:
            current_temperature = self._temperature(current["temperature_2m"])
            current_code = int(current["weather_code"])
            current_is_day = bool(int(current.get("is_day", 1)))
            forecast: list[ForecastDay] = []
            for index in range(5):
                high = self._temperature(highs[index])
                low = self._temperature(lows[index])
                representative = (
                    self._temperature(means[index])
                    if isinstance(means[index], (int, float)) and not isinstance(means[index], bool)
                    else round((high + low) / 2)
                )
                code = current_code if index == 0 else int(codes[index])
                condition = normalize_wmo_code(code)
                forecast.append(
                    ForecastDay(
                        day=date.fromisoformat(str(times[index])),
                        temperature_c=current_temperature if index == 0 else representative,
                        high_c=high,
                        low_c=low,
                        condition_key=condition.condition_key,
                        visual_group=condition.visual_group,
                        is_day=current_is_day if index == 0 else None,
                    )
                )
        except (KeyError, TypeError, ValueError) as error:
            raise WeatherProviderError("Open-Meteo returned malformed weather values.") from error

        return WeatherReadModel(location=self._config.location_name, forecast=tuple(forecast))

    @staticmethod
    def _daily_values(daily: dict[str, object], key: str) -> list[object]:
        values = daily.get(key)
        if not isinstance(values, list):
            raise WeatherProviderError(f"Open-Meteo response is missing daily field {key}.")
        return values

    @staticmethod
    def _temperature(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise WeatherProviderError("Open-Meteo returned a non-numeric temperature.")
        return round(float(value))

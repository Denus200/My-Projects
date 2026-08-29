from __future__ import annotations

from datetime import date, timedelta

from overlord.modules.weather.read_models import ForecastDay, WeatherGroup, WeatherReadModel


class MockWeatherProvider:
    """Deterministic local forecast used until a live provider is approved."""

    _DAYS = (
        (24, 31, 14, "sunny", WeatherGroup.SUNNY),
        (20, 25, 13, "rainy", WeatherGroup.RAINY),
        (17, 21, 11, "cloudy", WeatherGroup.CLOUDY),
        (-1, 2, -5, "snowy", WeatherGroup.SNOWY),
        (22, 27, 15, "sunny", WeatherGroup.SUNNY),
    )

    def __init__(self, *, start_day: date | None = None, location: str = "Manchester") -> None:
        self._start_day = start_day or date.today()
        self._location = location

    def forecast(self) -> WeatherReadModel:
        days = tuple(
            ForecastDay(
                day=self._start_day + timedelta(days=index),
                temperature_c=temperature,
                high_c=high,
                low_c=low,
                condition_key=condition,
                visual_group=group,
            )
            for index, (temperature, high, low, condition, group) in enumerate(self._DAYS)
        )
        return WeatherReadModel(location=self._location, forecast=days)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from overlord.modules.weather.read_models import WeatherReadModel


class WeatherProvider(Protocol):
    def forecast(self) -> WeatherReadModel: ...


@dataclass(frozen=True, slots=True)
class CachedWeather:
    weather: WeatherReadModel
    saved_at: datetime


class WeatherCache(Protocol):
    def load(self) -> CachedWeather | None: ...

    def save(self, value: CachedWeather) -> None: ...

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class WeatherGroup(StrEnum):
    SUNNY = "sunny"
    RAINY = "rainy"
    CLOUDY = "cloudy"
    SNOWY = "snowy"


@dataclass(frozen=True, slots=True)
class ForecastDay:
    day: date
    temperature_c: int
    high_c: int
    low_c: int
    condition_key: str
    visual_group: WeatherGroup
    is_day: bool | None = None


@dataclass(frozen=True, slots=True)
class WeatherReadModel:
    location: str
    forecast: tuple[ForecastDay, ...]

    @property
    def available(self) -> bool:
        return bool(self.forecast)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeatherConfig:
    location_name: str
    region: str
    latitude: float
    longitude: float
    timezone: str

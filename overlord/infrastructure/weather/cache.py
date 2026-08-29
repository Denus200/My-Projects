from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

from overlord.modules.weather.provider import CachedWeather
from overlord.modules.weather.read_models import ForecastDay, WeatherGroup, WeatherReadModel


class JsonWeatherCache:
    VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> CachedWeather | None:
        if not self.path.is_file():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("version") != self.VERSION:
            return None
        weather = payload.get("weather")
        if not isinstance(weather, dict):
            return None
        forecast = weather.get("forecast")
        if not isinstance(forecast, list):
            return None
        days = tuple(self._day_from_json(value) for value in forecast)
        saved_at = datetime.fromisoformat(str(payload["saved_at"]).replace("Z", "+00:00"))
        if saved_at.tzinfo is None:
            saved_at = saved_at.replace(tzinfo=timezone.utc)
        return CachedWeather(
            WeatherReadModel(location=str(weather["location"]), forecast=days),
            saved_at.astimezone(timezone.utc),
        )

    def save(self, value: CachedWeather) -> None:
        payload = {
            "version": self.VERSION,
            "saved_at": value.saved_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "weather": {
                "location": value.weather.location,
                "forecast": [self._day_to_json(day) for day in value.weather.forecast],
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _day_to_json(day: ForecastDay) -> dict[str, object]:
        return {
            "day": day.day.isoformat(),
            "temperature_c": day.temperature_c,
            "high_c": day.high_c,
            "low_c": day.low_c,
            "condition_key": day.condition_key,
            "visual_group": day.visual_group.value,
            "is_day": day.is_day,
        }

    @staticmethod
    def _day_from_json(value: object) -> ForecastDay:
        if not isinstance(value, dict):
            raise ValueError("Invalid cached weather day.")
        return ForecastDay(
            day=date.fromisoformat(str(value["day"])),
            temperature_c=int(value["temperature_c"]),
            high_c=int(value["high_c"]),
            low_c=int(value["low_c"]),
            condition_key=str(value["condition_key"]),
            visual_group=WeatherGroup(str(value["visual_group"])),
            is_day=None if value.get("is_day") is None else bool(value["is_day"]),
        )

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from threading import Lock
from typing import Callable

from overlord.modules.weather.provider import CachedWeather, WeatherCache, WeatherProvider
from overlord.modules.weather.read_models import WeatherReadModel


@dataclass(frozen=True, slots=True)
class WeatherRefreshResult:
    updated: bool
    failed: bool = False


class WeatherService:
    def __init__(
        self,
        provider: WeatherProvider,
        cache: WeatherCache,
        *,
        location_name: str,
        refresh_interval: timedelta = timedelta(minutes=30),
        retry_interval: timedelta = timedelta(minutes=5),
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._location_name = location_name
        self._refresh_interval = refresh_interval
        self._retry_interval = retry_interval
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = Lock()
        self._refreshing = False
        self._last_attempt_at: datetime | None = None
        self._last_attempt_failed = False
        self._logger = logging.getLogger("overlord.weather")
        self._cached = self._load_cache()

    def snapshot(self) -> WeatherReadModel:
        with self._lock:
            if self._cached is not None:
                return self._cached.weather
        return WeatherReadModel(location=self._location_name, forecast=())

    def refresh_if_stale(self, *, force: bool = False) -> WeatherRefreshResult:
        with self._lock:
            cached = self._cached
            if not force and cached is not None and self._now() - cached.saved_at < self._refresh_interval:
                return WeatherRefreshResult(updated=False)
            if self._refreshing:
                return WeatherRefreshResult(updated=False)
            self._refreshing = True

        try:
            weather = self._provider.forecast()
            if not weather.available:
                raise ValueError("Weather provider returned no forecast days.")
            entry = CachedWeather(weather=weather, saved_at=self._now())
            self._cache.save(entry)
            with self._lock:
                self._cached = entry
                self._last_attempt_at = entry.saved_at
                self._last_attempt_failed = False
            return WeatherRefreshResult(updated=True)
        except Exception as error:
            self._logger.warning("weather_refresh_failed error_type=%s", type(error).__name__)
            with self._lock:
                self._last_attempt_at = self._now()
                self._last_attempt_failed = True
            return WeatherRefreshResult(updated=False, failed=True)
        finally:
            with self._lock:
                self._refreshing = False

    def next_refresh_delay_seconds(self) -> float:
        with self._lock:
            cached = self._cached
            last_attempt_at = self._last_attempt_at
            last_attempt_failed = self._last_attempt_failed
        if last_attempt_failed and last_attempt_at is not None:
            retry_remaining = self._retry_interval - (self._now() - last_attempt_at)
            return max(1.0, retry_remaining.total_seconds())
        if cached is None:
            return self._retry_interval.total_seconds()
        remaining = self._refresh_interval - (self._now() - cached.saved_at)
        return max(1.0, remaining.total_seconds())

    @property
    def refresh_interval_seconds(self) -> float:
        return self._refresh_interval.total_seconds()

    def _load_cache(self) -> CachedWeather | None:
        try:
            return self._cache.load()
        except Exception as error:
            self._logger.warning("weather_cache_load_failed error_type=%s", type(error).__name__)
            return None

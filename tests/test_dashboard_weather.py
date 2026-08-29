from __future__ import annotations

import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.infrastructure.weather.cache import JsonWeatherCache
from overlord.infrastructure.weather.config import MEREFA_WEATHER_CONFIG
from overlord.infrastructure.weather.mock import MockWeatherProvider
from overlord.infrastructure.weather.open_meteo import (
    OpenMeteoWeatherProvider,
    WeatherProviderError,
    normalize_wmo_code,
)
from overlord.modules.weather.application import WeatherService
from overlord.modules.weather.provider import CachedWeather
from overlord.modules.weather.read_models import ForecastDay, WeatherGroup, WeatherReadModel
from overlord.ui.components.weather import (
    WEATHER_CARD_HEIGHT,
    WEATHER_CARD_WIDTH,
    WEATHER_GLASS_HEIGHT,
    WEATHER_VISUAL_SIZE,
    build_weather_widget,
    weather_visual_presets,
)
from overlord.ui.design_system.icons import IconName
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.dashboard.page import build_dashboard


ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = ROOT / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _walk(control):
    yield control
    for name in ("title", "content"):
        content = getattr(control, name, None)
        if isinstance(content, ft.Control):
            yield from _walk(content)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control, role: str):
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class _MemoryCache:
    def __init__(self, value: CachedWeather | None = None):
        self.value = value

    def load(self):
        return self.value

    def save(self, value):
        self.value = value


class _Response:
    def __init__(self, payload: object):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._payload


class _FailingProvider:
    def __init__(self):
        self.calls = 0

    def forecast(self):
        self.calls += 1
        raise OSError("offline")


class _CountingProvider:
    def __init__(self, weather: WeatherReadModel):
        self.weather = weather
        self.calls = 0

    def forecast(self):
        self.calls += 1
        return self.weather


class DashboardWeatherTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 8, 12)
        self.weather = MockWeatherProvider(start_day=self.day).forecast()

    def test_mock_provider_returns_normalized_five_day_forecast(self):
        self.assertEqual("Manchester", self.weather.location)
        self.assertEqual(5, len(self.weather.forecast))
        self.assertEqual(self.day, self.weather.forecast[0].day)
        self.assertEqual(
            ["sunny", "rainy", "cloudy", "snowy", "sunny"],
            [item.visual_group.value for item in self.weather.forecast],
        )

    def test_open_meteo_provider_requests_merefa_fields_and_normalizes_current_and_daily_values(self):
        payload = {
            "timezone": "Europe/Kyiv",
            "current": {"temperature_2m": 12.6, "weather_code": 61, "is_day": 0},
            "daily": {
                "time": ["2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15", "2026-08-16"],
                "weather_code": [0, 2, 3, 63, 75],
                "temperature_2m_max": [20.4, 21.4, 22.4, 18.4, 2.4],
                "temperature_2m_min": [10.4, 11.4, 12.4, 9.4, -4.4],
                "temperature_2m_mean": [15.4, 16.6, 17.6, 13.6, -1.2],
            },
        }
        captured = {}

        def opener(request, *, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return _Response(payload)

        weather = OpenMeteoWeatherProvider(MEREFA_WEATHER_CONFIG, opener=opener).forecast()
        query = parse_qs(urlparse(captured["url"]).query)
        self.assertEqual("Merefa", weather.location)
        self.assertEqual("49.8211", query["latitude"][0])
        self.assertEqual("36.0567", query["longitude"][0])
        self.assertEqual("Europe/Kyiv", query["timezone"][0])
        self.assertEqual("5", query["forecast_days"][0])
        self.assertEqual("temperature_2m,weather_code,is_day", query["current"][0])
        self.assertIn("temperature_2m_mean", query["daily"][0])
        self.assertEqual(8.0, captured["timeout"])
        self.assertEqual(13, weather.forecast[0].temperature_c)
        self.assertEqual(20, weather.forecast[0].high_c)
        self.assertEqual(10, weather.forecast[0].low_c)
        self.assertEqual("light_rain", weather.forecast[0].condition_key)
        self.assertEqual(WeatherGroup.RAINY, weather.forecast[0].visual_group)
        self.assertFalse(weather.forecast[0].is_day)
        self.assertEqual(17, weather.forecast[1].temperature_c)
        self.assertEqual("partly_cloudy", weather.forecast[1].condition_key)
        widget = build_weather_widget(weather, LIGHT_TOKENS)
        tabs = _role(widget, "weather-day-tab")
        self.assertEqual(
            ["2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15", "2026-08-16"],
            [tab.data["day"] for tab in tabs],
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            tabs[1].on_click(None)
        self.assertEqual("17", _role(widget, "weather-temperature")[0].value)
        self.assertEqual("Partly cloudy", _role(widget, "weather-condition")[0].value)
        self.assertEqual(
            "icons/lucide/cloud-sun.svg",
            _role(widget, "weather-condition-icon")[0].content.src,
        )

    def test_future_temperature_falls_back_to_high_low_midpoint_when_mean_is_unavailable(self):
        payload = {
            "current": {"temperature_2m": 10, "weather_code": 0, "is_day": 1},
            "daily": {
                "time": ["2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15", "2026-08-16"],
                "weather_code": [0, 1, 2, 3, 45],
                "temperature_2m_max": [20, 21, 22, 23, 24],
                "temperature_2m_min": [10, 11, 12, 13, 14],
            },
        }
        provider = OpenMeteoWeatherProvider(
            MEREFA_WEATHER_CONFIG,
            opener=lambda *_args, **_kwargs: _Response(payload),
        )
        weather = provider.forecast()
        self.assertEqual(16, weather.forecast[1].temperature_c)

    def test_wmo_normalization_covers_all_required_families_and_rejects_unknown_codes(self):
        expected = {
            0: WeatherGroup.SUNNY,
            1: WeatherGroup.SUNNY,
            2: WeatherGroup.CLOUDY,
            3: WeatherGroup.CLOUDY,
            45: WeatherGroup.CLOUDY,
            48: WeatherGroup.CLOUDY,
            51: WeatherGroup.RAINY,
            53: WeatherGroup.RAINY,
            55: WeatherGroup.RAINY,
            56: WeatherGroup.RAINY,
            57: WeatherGroup.RAINY,
            61: WeatherGroup.RAINY,
            63: WeatherGroup.RAINY,
            65: WeatherGroup.RAINY,
            66: WeatherGroup.RAINY,
            67: WeatherGroup.RAINY,
            71: WeatherGroup.SNOWY,
            73: WeatherGroup.SNOWY,
            75: WeatherGroup.SNOWY,
            77: WeatherGroup.SNOWY,
            80: WeatherGroup.RAINY,
            81: WeatherGroup.RAINY,
            82: WeatherGroup.RAINY,
            85: WeatherGroup.SNOWY,
            86: WeatherGroup.SNOWY,
            95: WeatherGroup.RAINY,
            96: WeatherGroup.RAINY,
            99: WeatherGroup.RAINY,
        }
        self.assertEqual(expected, {code: normalize_wmo_code(code).visual_group for code in expected})
        with self.assertRaises(WeatherProviderError):
            normalize_wmo_code(1000)

    def test_malformed_open_meteo_response_is_contained_as_provider_error(self):
        provider = OpenMeteoWeatherProvider(
            MEREFA_WEATHER_CONFIG,
            opener=lambda *_args, **_kwargs: _Response({"current": {}, "daily": {}}),
        )
        with self.assertRaises(WeatherProviderError):
            provider.forecast()

    def test_json_cache_round_trip_preserves_only_normalized_weather(self):
        path = TEST_TEMP_ROOT / f"weather-cache-{uuid.uuid4().hex}.json"
        try:
            cache = JsonWeatherCache(path)
            saved_at = datetime(2026, 8, 12, 12, tzinfo=timezone.utc)
            cache.save(CachedWeather(self.weather, saved_at))
            loaded = cache.load()
            self.assertIsNotNone(loaded)
            self.assertEqual(self.weather, loaded.weather)
            self.assertEqual(saved_at, loaded.saved_at)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["version"])
            self.assertNotIn("current", payload)
            self.assertNotIn("daily", payload)
        finally:
            path.unlink(missing_ok=True)
            path.with_suffix(".json.tmp").unlink(missing_ok=True)

    def test_service_uses_cache_immediately_refreshes_once_per_window_and_keeps_cache_offline(self):
        clock = [datetime(2026, 8, 12, 12, tzinfo=timezone.utc)]
        cache = _MemoryCache()
        provider = _CountingProvider(self.weather)
        service = WeatherService(
            provider,
            cache,
            location_name="Merefa",
            now=lambda: clock[0],
        )
        self.assertFalse(service.snapshot().available)
        self.assertTrue(service.refresh_if_stale().updated)
        self.assertEqual(1, provider.calls)
        self.assertEqual(self.weather, service.snapshot())
        self.assertFalse(service.refresh_if_stale().updated)
        self.assertEqual(1, provider.calls)

        clock[0] += timedelta(minutes=31)
        self.assertTrue(service.refresh_if_stale().updated)
        self.assertEqual(2, provider.calls)

        failing = _FailingProvider()
        offline = WeatherService(
            failing,
            cache,
            location_name="Merefa",
            now=lambda: clock[0] + timedelta(hours=1),
        )
        result = offline.refresh_if_stale(force=True)
        self.assertTrue(result.failed)
        self.assertEqual(self.weather, offline.snapshot())
        self.assertEqual(300, offline.next_refresh_delay_seconds())

    def test_no_cache_and_offline_provider_returns_unavailable_card_without_dashboard_failure(self):
        provider = _FailingProvider()
        service = WeatherService(provider, _MemoryCache(), location_name="Merefa")
        self.assertTrue(service.refresh_if_stale(force=True).failed)
        snapshot = service.snapshot()
        self.assertFalse(snapshot.available)
        widget = build_weather_widget(snapshot, LIGHT_TOKENS)
        self.assertFalse(widget.data["available"])
        self.assertEqual("Merefa", _role(widget, "weather-location")[0].value)
        self.assertEqual("Weather unavailable", _role(widget, "weather-unavailable")[0].value)

    def test_widget_matches_reference_geometry_and_glass_treatment(self):
        widget = build_weather_widget(self.weather, LIGHT_TOKENS)
        self.assertEqual(WEATHER_CARD_WIDTH, widget.width)
        self.assertEqual(WEATHER_CARD_HEIGHT, widget.height)
        self.assertEqual("#F7F7F7", widget.bgcolor)
        self.assertEqual(16, widget.border_radius)

        visual = _role(widget, "weather-visual")[0]
        self.assertEqual((WEATHER_VISUAL_SIZE, WEATHER_VISUAL_SIZE), (visual.width, visual.height))
        glass = _role(widget, "weather-glass-panel")[0]
        self.assertEqual(WEATHER_CARD_HEIGHT - WEATHER_GLASS_HEIGHT, glass.top)
        self.assertEqual(12, glass.blur.sigma_x)
        self.assertEqual(12, glass.blur.sigma_y)
        self.assertEqual(0.10, glass.data["fill_opacity"])
        self.assertEqual(85, glass.data["figma_refraction"])

    def test_visual_presets_use_source_assets_lucide_icons_and_five_tinted_shadows(self):
        presets = weather_visual_presets(LIGHT_TOKENS)
        self.assertEqual(set(WeatherGroup), set(presets))
        self.assertEqual(IconName.SUN, presets[WeatherGroup.SUNNY].icon_name)
        self.assertEqual(IconName.CLOUD_RAIN, presets[WeatherGroup.RAINY].icon_name)
        self.assertEqual(IconName.CLOUD, presets[WeatherGroup.CLOUDY].icon_name)
        self.assertEqual(IconName.SNOWFLAKE, presets[WeatherGroup.SNOWY].icon_name)
        self.assertEqual("#8D3C07", presets[WeatherGroup.SUNNY].shadow_color_base)
        self.assertEqual("#192776", presets[WeatherGroup.RAINY].shadow_color_base)
        self.assertEqual("#415D7C", presets[WeatherGroup.CLOUDY].shadow_color_base)
        self.assertEqual("#526A82", presets[WeatherGroup.SNOWY].shadow_color_base)
        self.assertTrue(all(len(preset.shadow_layers) == 5 for preset in presets.values()))
        self.assertEqual(
            [(10, 22), (39, 39), (88, 53), (157, 63), (245, 69)],
            [(layer.y_offset, layer.blur_radius) for layer in presets[WeatherGroup.SUNNY].shadow_layers],
        )

        for preset in presets.values():
            self.assertTrue((ROOT / "assets" / preset.animation_asset).is_file())
            self.assertTrue((ROOT / "assets" / "icons" / "lucide" / f"{preset.icon_name.value}.svg").is_file())
        self.assertTrue((ROOT / "assets" / "icons" / "lucide" / "cloud-sun.svg").is_file())
        self.assertTrue((ROOT / "assets" / "icons" / "lucide" / "cloud-lightning.svg").is_file())

        thunderstorm = WeatherReadModel(
            location="Merefa",
            forecast=(
                ForecastDay(
                    self.day,
                    18,
                    21,
                    14,
                    "thunderstorm",
                    WeatherGroup.RAINY,
                ),
            ),
        )
        thunderstorm_widget = build_weather_widget(thunderstorm, LIGHT_TOKENS)
        self.assertEqual(
            "icons/lucide/cloud-lightning.svg",
            _role(thunderstorm_widget, "weather-condition-icon")[0].content.src,
        )

    def test_day_switching_updates_the_full_visual_preset_without_rebuilding_dashboard(self):
        widget = build_weather_widget(self.weather, LIGHT_TOKENS)
        tabs = _role(widget, "weather-day-tab")
        self.assertEqual(5, len(tabs))

        expected = (
            ("sunny", "weather/sunny.gif", "icons/lucide/sun.svg", "24"),
            ("rainy", "weather/rainy.gif", "icons/lucide/cloud-rain.svg", "20"),
            ("cloudy", "weather/cloudy.gif", "icons/lucide/cloud.svg", "17"),
            ("snowy", "weather/snowy.gif", "icons/lucide/snowflake.svg", "-1"),
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            for index, (group, asset, icon, temperature) in enumerate(expected):
                tabs[index].on_click(None)
                self.assertEqual(index, widget.data["selected_index"])
                self.assertEqual(group, widget.data["selected_group"])
                self.assertEqual(asset, _role(widget, "weather-visual")[0].src)
                self.assertEqual(icon, _role(widget, "weather-condition-icon")[0].content.src)
                self.assertEqual(temperature, _role(widget, "weather-temperature")[0].value)
                self.assertEqual(5, len(_role(widget, "weather-visual-shadow")[0].shadow))
                self.assertTrue(tabs[index].data["selected"])

    def test_dashboard_placement_resize_and_sidebar_relayout_never_issue_weather_requests(self):
        path = TEST_TEMP_ROOT / f"dashboard-weather-{uuid.uuid4().hex}.db"
        try:
            services = bootstrap(path).services
            self.assertEqual(
                path.with_name(f"{path.stem}-weather-cache.json"),
                services.weather._cache.path,
            )
            provider = _CountingProvider(self.weather)
            services.weather._provider = provider
            collapsed = [False]
            dashboard = build_dashboard(
                services,
                LIGHT_TOKENS,
                f"/dashboard?date={self.day.isoformat()}",
                lambda *_: None,
                lambda: None,
                self.fail,
                sidebar_collapsed=lambda: collapsed[0],
            )
            upper = _role(dashboard, "dashboard-upper")[0]
            self.assertEqual(16, upper.spacing)
            self.assertEqual("first-bento-row", upper.controls[0].data["role"])
            self.assertEqual("weather-widget", upper.controls[1].data["role"])
            self.assertEqual(16, upper.data["weather_gap"])
            self.assertEqual(16, upper.controls[0].data["widget_gap"])
            row = upper.controls[0]
            board = _role(row, "three-day-task-board")[0]
            with patch.object(ft.Control, "update", lambda _control: None):
                row.on_size_change(SimpleNamespace(width=1640))
                board.on_size_change(SimpleNamespace(width=900))
                collapsed[0] = True
                row.on_size_change(SimpleNamespace(width=1816))
                board.on_size_change(SimpleNamespace(width=1300))
            self.assertEqual(0, provider.calls)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

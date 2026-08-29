from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from overlord.modules.weather.read_models import ForecastDay, WeatherGroup, WeatherReadModel
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import format_weekday_name, ui_text


WEATHER_CARD_WIDTH = 448
WEATHER_CARD_HEIGHT = 461
WEATHER_VISUAL_SIZE = 300
WEATHER_GLASS_HEIGHT = 192


@dataclass(frozen=True, slots=True)
class WeatherShadowLayer:
    y_offset: int
    blur_radius: int
    opacity: float


@dataclass(frozen=True, slots=True)
class WeatherVisualPreset:
    group: WeatherGroup
    animation_asset: str
    shadow_color_base: str
    shadow_layers: tuple[WeatherShadowLayer, ...]
    icon_name: IconName
    icon_color: str
    icon_background: str
    glass_accent: str


_SHADOW_LAYERS = (
    WeatherShadowLayer(10, 22, 0.08),
    WeatherShadowLayer(39, 39, 0.07),
    WeatherShadowLayer(88, 53, 0.04),
    WeatherShadowLayer(157, 63, 0.01),
    WeatherShadowLayer(245, 69, 0.004),
)

_CONDITION_ICONS = {
    "partly_cloudy": IconName.CLOUD_SUN,
    "thunderstorm": IconName.CLOUD_LIGHTNING,
    "thunderstorm_hail": IconName.CLOUD_LIGHTNING,
    "heavy_thunderstorm_hail": IconName.CLOUD_LIGHTNING,
}


def _condition_icon(forecast: ForecastDay, preset: WeatherVisualPreset) -> IconName:
    return _CONDITION_ICONS.get(forecast.condition_key, preset.icon_name)


def weather_visual_presets(tokens: ThemeTokens) -> dict[WeatherGroup, WeatherVisualPreset]:
    return {
        WeatherGroup.SUNNY: WeatherVisualPreset(
            WeatherGroup.SUNNY,
            "weather/sunny.gif",
            tokens.weather_sunny_shadow,
            _SHADOW_LAYERS,
            IconName.SUN,
            tokens.weather_sunny_icon,
            tokens.weather_sunny_icon_background,
            tokens.weather_sunny_icon,
        ),
        WeatherGroup.RAINY: WeatherVisualPreset(
            WeatherGroup.RAINY,
            "weather/rainy.gif",
            tokens.weather_rainy_shadow,
            _SHADOW_LAYERS,
            IconName.CLOUD_RAIN,
            tokens.weather_rainy_icon,
            tokens.weather_rainy_icon_background,
            tokens.weather_rainy_icon,
        ),
        WeatherGroup.CLOUDY: WeatherVisualPreset(
            WeatherGroup.CLOUDY,
            "weather/cloudy.gif",
            tokens.weather_cloudy_shadow,
            _SHADOW_LAYERS,
            IconName.CLOUD,
            tokens.weather_cloudy_icon,
            tokens.weather_cloudy_icon_background,
            tokens.weather_cloudy_icon,
        ),
        WeatherGroup.SNOWY: WeatherVisualPreset(
            WeatherGroup.SNOWY,
            "weather/snowy.gif",
            tokens.weather_snowy_shadow,
            _SHADOW_LAYERS,
            IconName.SNOWFLAKE,
            tokens.weather_snowy_icon,
            tokens.weather_snowy_icon_background,
            tokens.weather_snowy_icon,
        ),
    }


def _with_opacity(color: str, opacity: float) -> str:
    normalized = color.removeprefix("#")
    if len(normalized) == 8:
        normalized = normalized[2:]
    alpha = max(1, min(255, round(opacity * 255)))
    return f"#{alpha:02X}{normalized}"


def _shadows(preset: WeatherVisualPreset) -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=layer.blur_radius,
            color=_with_opacity(preset.shadow_color_base, layer.opacity),
            offset=ft.Offset(0, layer.y_offset),
        )
        for layer in preset.shadow_layers
    ]


def _day_label(day: ForecastDay) -> str:
    return f"{format_weekday_name(day.day)[:3]} {day.day.day}"


def _unavailable_weather_widget(data: WeatherReadModel, tokens: ThemeTokens) -> ft.Control:
    return ft.Container(
        ft.Stack(
            [
                ft.Text(
                    data.location,
                    left=20,
                    top=23,
                    color=tokens.text_primary,
                    size=tokens.text_title,
                    weight=ft.FontWeight.W_400,
                    data={"role": "weather-location"},
                ),
                ft.Text(
                    ui_text("weather.unavailable"),
                    left=20,
                    top=50,
                    color=tokens.text_muted,
                    size=tokens.text_body,
                    data={"role": "weather-unavailable"},
                ),
            ],
            width=WEATHER_CARD_WIDTH,
            height=WEATHER_CARD_HEIGHT,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ),
        width=WEATHER_CARD_WIDTH,
        height=WEATHER_CARD_HEIGHT,
        bgcolor=tokens.weather_card_background,
        border=ft.Border.all(tokens.border_width, tokens.weather_card_border),
        border_radius=tokens.space_4,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={
            "role": "weather-widget",
            "preferred_width": WEATHER_CARD_WIDTH,
            "preferred_height": WEATHER_CARD_HEIGHT,
            "available": False,
        },
    )


def build_weather_widget(data: WeatherReadModel, tokens: ThemeTokens) -> ft.Control:
    if not data.forecast:
        return _unavailable_weather_widget(data, tokens)

    presets = weather_visual_presets(tokens)
    initial = data.forecast[0]
    initial_preset = presets[initial.visual_group]
    initial_condition = ui_text(f"weather.condition.{initial.condition_key}")

    high_low = ft.Text(
        ui_text("weather.high_low", high=initial.high_c, low=initial.low_c),
        color=tokens.text_muted,
        size=tokens.text_body,
        data={"role": "weather-high-low"},
    )
    temperature = ft.Text(
        str(initial.temperature_c),
        color=tokens.text_primary,
        size=64,
        weight=ft.FontWeight.W_400,
        data={"role": "weather-temperature"},
    )
    temperature_unit = ft.Text(
        "°C",
        color=tokens.text_primary,
        size=32,
        weight=ft.FontWeight.W_400,
        opacity=0.75,
    )
    temperature_row = ft.Row(
        [temperature, ft.Container(temperature_unit, margin=ft.Margin.only(top=12))],
        spacing=0,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
        data={"role": "weather-temperature-display"},
    )
    condition = ft.Text(
        initial_condition,
        color=tokens.text_primary,
        size=tokens.text_emphasis,
        data={"role": "weather-condition"},
    )
    visual_shadow = ft.Container(
        width=WEATHER_VISUAL_SIZE,
        height=WEATHER_VISUAL_SIZE,
        border_radius=WEATHER_VISUAL_SIZE / 2,
        bgcolor=_with_opacity(initial_preset.shadow_color_base, 0.01),
        shadow=_shadows(initial_preset),
        left=74,
        top=80,
        ignore_interactions=True,
        data={"role": "weather-visual-shadow", "layer_count": len(initial_preset.shadow_layers)},
    )
    visual = ft.Image(
        src=initial_preset.animation_asset,
        width=WEATHER_VISUAL_SIZE,
        height=WEATHER_VISUAL_SIZE,
        left=74,
        top=80,
        fit=ft.BoxFit.CONTAIN,
        border_radius=WEATHER_VISUAL_SIZE / 2,
        gapless_playback=True,
        semantics_label=ui_text("weather.visual_label", condition=initial_condition),
        data={"role": "weather-visual", "group": initial.visual_group.value},
    )
    glass = ft.Container(
        left=0,
        right=0,
        top=WEATHER_CARD_HEIGHT - WEATHER_GLASS_HEIGHT,
        bottom=0,
        bgcolor=tokens.weather_glass_fill,
        blur=ft.Blur(12, 12),
        border=ft.Border.only(
            top=ft.BorderSide(tokens.border_width, _with_opacity(initial_preset.glass_accent, 0.16))
        ),
        ignore_interactions=True,
        data={
            "role": "weather-glass-panel",
            "frost": 12,
            "fill_opacity": 0.10,
            "figma_light": 0.24,
            "figma_refraction": 85,
            "figma_dispersion": 50,
        },
    )
    condition_icon = lucide_icon(
        _condition_icon(initial, initial_preset),
        color=initial_preset.icon_color,
        size=60,
        label=ui_text("weather.icon_label", condition=initial_condition),
        show_tooltip=False,
    )
    icon_surface = ft.Container(
        condition_icon,
        width=84,
        height=84,
        right=20,
        top=289,
        alignment=ft.Alignment.CENTER,
        bgcolor=initial_preset.icon_background,
        border_radius=42,
        data={"role": "weather-condition-icon", "group": initial.visual_group.value},
    )

    day_surfaces: list[ft.Container] = []
    root: ft.Container

    def day_style() -> ft.ButtonStyle:
        return ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: tokens.text_primary},
            bgcolor={ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
            overlay_color={
                ft.ControlState.HOVERED: tokens.interactive_hover,
                ft.ControlState.PRESSED: tokens.interactive_pressed,
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
            },
            side={
                ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
            },
            elevation=0,
            padding=0,
            shape=ft.RoundedRectangleBorder(radius=tokens.space_2),
        )

    def select_day(index: int, *, update: bool = True) -> None:
        forecast = data.forecast[index]
        preset = presets[forecast.visual_group]
        condition_label = ui_text(f"weather.condition.{forecast.condition_key}")

        high_low.value = ui_text("weather.high_low", high=forecast.high_c, low=forecast.low_c)
        temperature.value = str(forecast.temperature_c)
        condition.value = condition_label
        visual.src = preset.animation_asset
        visual.semantics_label = ui_text("weather.visual_label", condition=condition_label)
        visual.data.update({"group": forecast.visual_group.value})
        visual_shadow.bgcolor = _with_opacity(preset.shadow_color_base, 0.01)
        visual_shadow.shadow = _shadows(preset)
        condition_icon.src = f"icons/lucide/{_condition_icon(forecast, preset).value}.svg"
        condition_icon.color = preset.icon_color
        condition_icon.semantics_label = ui_text("weather.icon_label", condition=condition_label)
        icon_surface.bgcolor = preset.icon_background
        icon_surface.data.update({"group": forecast.visual_group.value})
        glass.border = ft.Border.only(
            top=ft.BorderSide(tokens.border_width, _with_opacity(preset.glass_accent, 0.16))
        )

        for tab_index, surface in enumerate(day_surfaces):
            selected = tab_index == index
            surface.bgcolor = tokens.weather_tab_active_background if selected else ft.Colors.TRANSPARENT
            surface.shadow = (
                ft.BoxShadow(
                    blur_radius=2,
                    color=tokens.weather_tab_shadow,
                    offset=ft.Offset(0, 2),
                )
                if selected
                else None
            )
            surface.data["selected"] = selected
            surface.content.data["selected"] = selected

        root.data.update(
            {
                "selected_index": index,
                "selected_day": forecast.day.isoformat(),
                "selected_group": forecast.visual_group.value,
            }
        )
        if update:
            root.update()

    for index, forecast in enumerate(data.forecast[:5]):
        label = _day_label(forecast)
        button = ft.TextButton(
            label,
            height=42,
            expand=True,
            tooltip=ui_text("weather.select_day", day=label),
            on_click=lambda _event, selected=index: select_day(selected),
            style=day_style(),
            data={
                "role": "weather-day-tab",
                "index": index,
                "day": forecast.day.isoformat(),
                "selected": index == 0,
            },
        )
        surface = ft.Container(
            button,
            height=42,
            expand=True,
            bgcolor=tokens.weather_tab_active_background if index == 0 else ft.Colors.TRANSPARENT,
            border_radius=tokens.space_2,
            shadow=(
                ft.BoxShadow(
                    blur_radius=2,
                    color=tokens.weather_tab_shadow,
                    offset=ft.Offset(0, 2),
                )
                if index == 0
                else None
            ),
            data={"role": "weather-day-tab-surface", "index": index, "selected": index == 0},
        )
        day_surfaces.append(surface)

    stack = ft.Stack(
        [
            visual_shadow,
            visual,
            glass,
            ft.Text(
                data.location,
                left=20,
                top=23,
                color=tokens.text_primary,
                size=tokens.text_title,
                weight=ft.FontWeight.W_400,
                data={"role": "weather-location"},
            ),
            ft.Container(high_low, left=20, top=50),
            ft.Container(temperature_row, left=20, top=276),
            ft.Container(condition, left=20, top=368),
            icon_surface,
            ft.Container(
                ft.Row(day_surfaces, spacing=tokens.space_1),
                left=20,
                right=20,
                bottom=20,
                height=42,
                data={"role": "weather-day-switcher", "day_count": len(day_surfaces)},
            ),
        ],
        width=WEATHER_CARD_WIDTH,
        height=WEATHER_CARD_HEIGHT,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    root = ft.Container(
        stack,
        width=WEATHER_CARD_WIDTH,
        height=WEATHER_CARD_HEIGHT,
        bgcolor=tokens.weather_card_background,
        border=ft.Border.all(tokens.border_width, tokens.weather_card_border),
        border_radius=tokens.space_4,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={
            "role": "weather-widget",
            "preferred_width": WEATHER_CARD_WIDTH,
            "preferred_height": WEATHER_CARD_HEIGHT,
            "selected_index": 0,
            "selected_day": initial.day.isoformat(),
            "selected_group": initial.visual_group.value,
            "available": True,
        },
    )
    return root

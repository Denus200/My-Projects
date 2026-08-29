from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import flet as ft
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from overlord.infrastructure.weather.mock import MockWeatherProvider
from overlord.ui.components.weather import build_weather_widget
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS


OUTPUT_ROOT = ROOT / "artifacts" / "dashboard-weather"
REFERENCE = Path(r"C:\Users\Den\Downloads\Нова папка (2)\5\Weather Card.png")


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control: ft.Control, role: str) -> list[ft.Control]:
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


def _compose(reference_crop: tuple[int, int, int, int], implementation: Path, output: Path) -> None:
    with Image.open(REFERENCE) as source_image, Image.open(implementation) as built_image:
        source = source_image.convert("RGB").crop(reference_crop)
        built = built_image.convert("RGB")
        label_height = 30
        canvas = Image.new("RGB", (896, 461 + label_height), "white")
        canvas.paste(source, (0, label_height))
        canvas.paste(built, (448, label_height))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        draw.text((12, 10), "REFERENCE", fill="#17131A", font=font)
        draw.text((460, 10), "IMPLEMENTATION", fill="#17131A", font=font)
        draw.line((448, 0, 448, canvas.height), fill="#D61F45", width=2)
        canvas.save(output)


async def main(page: ft.Page) -> None:
    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    page.window.width = 488
    page.window.height = 520

    forecast = MockWeatherProvider(start_day=date(2026, 8, 12)).forecast()
    widget = build_weather_widget(forecast, LIGHT_TOKENS)
    screenshot = ft.Screenshot(widget)
    page.add(screenshot)
    page.update()
    await asyncio.sleep(1.5)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    sunny = OUTPUT_ROOT / "01-sunny.png"
    sunny.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    _role(widget, "weather-day-tab")[1].on_click(None)
    await asyncio.sleep(0.5)
    rainy = OUTPUT_ROOT / "02-rainy.png"
    rainy.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    sunny_comparison = OUTPUT_ROOT / "comparison-sunny.png"
    rainy_comparison = OUTPUT_ROOT / "comparison-rainy.png"
    _compose((20, 20, 468, 481), sunny, sunny_comparison)
    _compose((508, 20, 956, 481), rainy, rainy_comparison)
    print(sunny)
    print(rainy)
    print(sunny_comparison)
    print(rainy_comparison)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ROOT / "assets"))

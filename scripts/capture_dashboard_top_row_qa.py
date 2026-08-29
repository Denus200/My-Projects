from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import flet as ft
from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.dashboard.page import build_dashboard


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "dashboard-top-row"
DATABASE_PATH = REPOSITORY_ROOT / "data" / "test-tmp" / "dashboard-top-row-qa.db"
REFERENCE_PATH = Path(r"C:\Users\Den\Downloads\Нова папка (2)\5\Frame 318.png")


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control: ft.Control, role: str) -> ft.Control:
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict)
        and item.data.get("role") == role
    )


def _seed() -> tuple[object, date]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.unlink(missing_ok=True)
    services = bootstrap(DATABASE_PATH).services
    selected = date(2026, 8, 13)
    titles = (
        ("Review yesterday's notes", selected - timedelta(days=1), True),
        ("Filter email list", selected, True),
        ("Segment customer demographics", selected, False),
        ("Analyze open rates", selected, False),
        ("A/B test subject lines", selected, True),
        ("Sports", selected + timedelta(days=1), False),
        ("English Classes", selected + timedelta(days=1), False),
    )
    for index, (title, scheduled, completed) in enumerate(titles):
        task = services.tasks.create_task.execute(None, title, schedule_start_date=scheduled)
        if completed:
            services.tasks.complete_task.execute(
                task.id,
                active_time_minutes=60 + index * 15,
                total_time_minutes=90 + index * 30,
            )
    return services, selected


def _compose(reference: Path, implementation: Path, output: Path) -> None:
    with Image.open(reference) as source_image, Image.open(implementation) as implementation_image:
        source = source_image.convert("RGB")
        built = implementation_image.convert("RGB")
        comparison = Image.new(
            "RGB",
            (source.width + built.width, max(source.height, built.height)),
            "white",
        )
        comparison.paste(source, (0, 0))
        comparison.paste(built, (source.width, 0))
        comparison.save(output)


async def main(page: ft.Page) -> None:
    services, selected = _seed()
    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    page.window.width = 1660
    page.window.height = 480
    dashboard = build_dashboard(
        services,
        LIGHT_TOKENS,
        f"/dashboard?date={selected.isoformat()}",
        lambda *_: None,
        lambda: None,
        lambda error: print(error),
        page,
    )
    top_row = _role(dashboard, "first-bento-row")
    top_row.width = 1640
    screenshot = ft.Screenshot(top_row)
    page.add(screenshot)
    page.update()
    await asyncio.sleep(1)

    top_row.on_size_change(SimpleNamespace(width=1640))
    page.update()
    await asyncio.sleep(0.2)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    wide_path = OUTPUT_ROOT / "01-wide-1640x433.png"
    wide_path.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    top_row.width = 1120
    top_row.on_size_change(SimpleNamespace(width=1120))
    page.update()
    await asyncio.sleep(0.2)
    narrow_path = OUTPUT_ROOT / "02-narrow-1120x433.png"
    narrow_path.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    page.window.width = 1840
    top_row.width = 1816
    top_row.on_size_change(SimpleNamespace(width=1816))
    page.update()
    await asyncio.sleep(0.2)
    extra_wide_path = OUTPUT_ROOT / "03-extra-wide-1816x433.png"
    extra_wide_path.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    comparison_path = OUTPUT_ROOT / "comparison-wide.png"
    _compose(REFERENCE_PATH, wide_path, comparison_path)
    print(wide_path)
    print(narrow_path)
    print(extra_wide_path)
    print(comparison_path)
    DATABASE_PATH.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

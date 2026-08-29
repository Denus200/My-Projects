from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.demo import DEMO_DATABASE_PATH, ensure_demo_database
from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import Task, TaskLifecycle
from overlord.ui.components.task_card import TaskCardVariant, task_card
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.dashboard.page import build_dashboard

OUTPUT_PATH = REPOSITORY_ROOT / "artifacts" / "task-board-implementation.png"
COLLAPSED_OUTPUT_PATH = REPOSITORY_ROOT / "artifacts" / "task-board-collapsed-implementation.png"
HOVER_OUTPUT_PATH = REPOSITORY_ROOT / "artifacts" / "task-board-hover-implementation.png"
COMPACT_OUTPUT_PATH = REPOSITORY_ROOT / "artifacts" / "task-card-compact-implementation.png"
CAPTURE_COMPACT = "--compact" in sys.argv


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _task_card(control: ft.Control) -> ft.Container | None:
    return next(
        (
            item
            for item in _walk(control)
            if isinstance(item, ft.Container)
            and isinstance(getattr(item, "data", None), dict)
            and item.data.get("role") == "task-card"
        ),
        None,
    )


def _frontload(task_list: ft.ListView, predicate) -> ft.Container:
    for index, item in enumerate(task_list.controls):
        card = _task_card(item)
        if card is not None and predicate(card):
            task_list.controls.insert(0, task_list.controls.pop(index))
            return card
    raise RuntimeError("The demo data does not contain the required Task Card state.")


def _compact_reference() -> ft.Control:
    now = datetime.now()
    project_color = ("#79E6EC",)
    items = (
        TaskListItem(
            Task(9001, None, "Filter email list", TaskLifecycle.PLANNED, now, now),
            None,
        ),
        TaskListItem(
            Task(9002, None, "Filter email list", TaskLifecycle.COMPLETED, now, now),
            None,
        ),
    )
    cards = [
        task_card(
            item,
            LIGHT_TOKENS,
            variant=TaskCardVariant.COMPACT,
            project_colors=project_color,
        )
        for item in items
    ]
    for card in cards:
        card.width = 280
    return ft.Container(
        ft.Column(cards, spacing=22, tight=True),
        width=321,
        height=120,
        padding=ft.Padding.only(left=20, top=20, right=21),
        bgcolor=LIGHT_TOKENS.dashboard_board_background,
    )


async def main(page: ft.Page) -> None:
    ensure_demo_database(DEMO_DATABASE_PATH)
    services = bootstrap(DEMO_DATABASE_PATH).services
    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    if CAPTURE_COMPACT:
        screenshot = ft.Screenshot(_compact_reference())
        page.add(screenshot)
        page.update()
        await asyncio.sleep(1)
        COMPACT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        COMPACT_OUTPUT_PATH.write_bytes(await screenshot.capture(pixel_ratio=1.0))
        print(COMPACT_OUTPUT_PATH)
        await page.window.close()
        return
    dashboard = build_dashboard(
        services,
        LIGHT_TOKENS,
        "/dashboard",
        lambda *_: None,
        lambda: None,
        lambda error: print(error),
        page,
    )
    board = next(
        control
        for control in _walk(dashboard)
        if isinstance(getattr(control, "data", None), dict)
        and control.data.get("role") == "three-day-task-board"
    )
    task_lists = [
        control
        for control in _walk(board)
        if isinstance(control, ft.ListView)
        and isinstance(getattr(control, "data", None), dict)
        and control.data.get("role") == "day-task-list"
    ]
    _frontload(task_lists[2], lambda card: not card.data["completed"])
    board.width = 1176
    board.col = None
    screenshot = ft.Screenshot(board)
    page.add(screenshot)
    page.update()
    await asyncio.sleep(1)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(await screenshot.capture(pixel_ratio=1.0))
    board.width = 1300
    page.update()
    await asyncio.sleep(0.2)
    COLLAPSED_OUTPUT_PATH.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    hovered = _frontload(
        task_lists[1],
        lambda card: not card.data["completed"] and card.data["meta_chip_count"] > 0,
    )
    hovered.on_hover(SimpleNamespace(data="true"))
    board.width = 1176
    page.update()
    await asyncio.sleep(0.2)
    HOVER_OUTPUT_PATH.write_bytes(await screenshot.capture(pixel_ratio=1.0))

    print(OUTPUT_PATH)
    print(COLLAPSED_OUTPUT_PATH)
    print(HOVER_OUTPUT_PATH)
    await page.window.close()


if __name__ == "__main__":
    sys.argv = [argument for argument in sys.argv if argument != "--compact"]
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

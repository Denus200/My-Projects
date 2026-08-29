from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.app.read_models import TaskListItem
from overlord.bootstrap import bootstrap
from overlord.ui.components.complete_task import build_complete_task_dialog
from overlord.ui.components.task_card import TaskCardVariant, task_card
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "complete-task"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "complete-task-qa.db"


def _walk(control: ft.Control):
    yield control
    for name in ("title", "content"):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            yield from _walk(child)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control: ft.Control, role: str) -> ft.Control:
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    )


def _dialog_frame(dialog: ft.AlertDialog) -> ft.Container:
    return ft.Container(
        ft.Column(
            [dialog.title, dialog.content, *dialog.actions],
            spacing=LIGHT_TOKENS.space_4,
            tight=True,
        ),
        width=350,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_large,
        padding=ft.Padding.only(
            left=LIGHT_TOKENS.space_5,
            top=LIGHT_TOKENS.space_4,
            right=LIGHT_TOKENS.space_5,
            bottom=LIGHT_TOKENS.space_5,
        ),
    )


async def _capture(page: ft.Page, screenshot: ft.Screenshot, control: ft.Control, path: Path) -> None:
    screenshot.content = ft.Container(
        control,
        width=520,
        height=560,
        alignment=ft.Alignment.CENTER,
        bgcolor=LIGHT_TOKENS.app_background,
    )
    page.update()
    await asyncio.sleep(0.45)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await screenshot.capture(pixel_ratio=1.0))
    print(path)


async def main(page: ft.Page) -> None:
    QA_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    QA_DATABASE.unlink(missing_ok=True)
    services = bootstrap(QA_DATABASE).services
    today = date.today()
    existing = services.tasks.create_task.execute(
        None,
        "Prepare release notes",
        schedule_start_date=today,
        estimate_minutes=90,
    )
    missing = services.tasks.create_task.execute(
        None,
        "Unestimated follow-up",
        schedule_start_date=today,
    )

    page.padding = 0
    page.window.width = 560
    page.window.height = 630
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    screenshot = ft.Screenshot(ft.Container())
    page.add(screenshot)

    def dialog(task_id: int) -> ft.AlertDialog:
        return build_complete_task_dialog(
            services,
            task_id,
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
            print,
            selected_day=today,
        )

    existing_dialog = dialog(existing.id)
    await _capture(
        page,
        screenshot,
        _dialog_frame(existing_dialog),
        OUTPUT_ROOT / "01-existing-estimate-read-only.png",
    )

    missing_dialog = dialog(missing.id)
    await _capture(
        page,
        screenshot,
        _dialog_frame(missing_dialog),
        OUTPUT_ROOT / "02-missing-estimate-editable.png",
    )

    estimate_entered = dialog(missing.id)
    _role(estimate_entered, "complete-estimate-hours").value = "1"
    _role(estimate_entered, "complete-estimate-minutes").value = "30"
    await _capture(
        page,
        screenshot,
        _dialog_frame(estimate_entered),
        OUTPUT_ROOT / "03-estimate-entered.png",
    )

    manual_times = dialog(existing.id)
    _role(manual_times, "complete-total-hours").value = "24"
    _role(manual_times, "complete-total-minutes").value = "59"
    _role(manual_times, "complete-active-hours").value = "1"
    _role(manual_times, "complete-active-minutes").value = "30"
    await _capture(
        page,
        screenshot,
        _dialog_frame(manual_times),
        OUTPUT_ROOT / "04-total-and-active-entered.png",
    )

    large_hours = dialog(missing.id)
    _role(large_hours, "complete-estimate-hours").value = "150"
    _role(large_hours, "complete-estimate-minutes").value = "0"
    _role(large_hours, "complete-total-hours").value = "150"
    _role(large_hours, "complete-total-minutes").value = "0"
    _role(large_hours, "complete-active-hours").value = "150"
    _role(large_hours, "complete-active-minutes").value = "0"
    await _capture(
        page,
        screenshot,
        _dialog_frame(large_hours),
        OUTPUT_ROOT / "05-large-hours-fully-visible.png",
    )

    completed = services.tasks.complete_task.execute(
        existing.id,
        total_time_minutes=1499,
        active_time_minutes=90,
        selected_day=today,
    )
    completed_state = ft.Container(
        ft.Column(
            [
                ft.Text(
                    "Completed Tasks",
                    color=LIGHT_TOKENS.text_primary,
                    size=LIGHT_TOKENS.text_title,
                    weight=ft.FontWeight.W_700,
                ),
                task_card(
                    TaskListItem(completed, None),
                    LIGHT_TOKENS,
                    variant=TaskCardVariant.FULL,
                    allow_reopen=True,
                ),
            ],
            spacing=LIGHT_TOKENS.space_4,
            tight=True,
        ),
        width=420,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_large,
        padding=LIGHT_TOKENS.space_5,
    )
    await _capture(
        page,
        screenshot,
        completed_state,
        OUTPUT_ROOT / "06-completed-result.png",
    )

    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

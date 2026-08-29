from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.modules.projects.domain import ProjectStageStatus
from overlord.ui.components.date_time_picker import build_date_time_picker_dialog
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "create-task"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "create-task-qa.db"


def _walk(control: ft.Control):
    yield control
    for name in ("title", "content"):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            yield from _walk(child)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control: ft.Control, role: str) -> list[ft.Control]:
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict)
        and item.data.get("role") == role
    ]


def _dialog_frame(dialog: ft.AlertDialog, height: int) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                dialog.title,
                ft.Container(dialog.content, expand=True),
                *dialog.actions,
            ],
            spacing=LIGHT_TOKENS.space_4,
        ),
        width=600,
        height=height,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_large,
        padding=LIGHT_TOKENS.space_5,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def _overlay_frame(dialog: ft.AlertDialog) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                dialog.content,
                ft.Row(dialog.actions, alignment=ft.MainAxisAlignment.END),
            ],
            spacing=LIGHT_TOKENS.space_3,
            tight=True,
        ),
        width=530,
        height=430,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_large,
        padding=LIGHT_TOKENS.space_4,
    )


async def _capture(
    page: ft.Page,
    screenshot: ft.Screenshot,
    control: ft.Control,
    path: Path,
    width: int,
    height: int,
) -> None:
    page.window.width = width + 32
    page.window.height = min(height + 64, 1060)
    screenshot.content = ft.Container(
        control,
        width=width,
        height=height,
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
    titan = services.projects.create_project.execute("Titan", color="#FFC7D2")
    overlord = services.projects.create_project.execute("Overlord", color="#CCEFF3")
    inbox = services.projects.create_project.execute("Inbox", color="#F1ECEF")
    titan_plan = services.projects.create_plan.execute(titan.id, "Current")
    titan_stage = services.projects.create_stage.execute(titan.id, titan_plan.id, "UI Design")
    services.projects.change_stage_status.execute(titan_stage.id, ProjectStageStatus.IN_PROGRESS)
    overlord_plan = services.projects.create_plan.execute(overlord.id, "Stage 2")
    overlord_stage = services.projects.create_stage.execute(overlord.id, overlord_plan.id, "Projects")
    projects = services.projects.list_projects.execute()

    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    screenshot = ft.Screenshot(ft.Container())
    page.add(screenshot)
    dialog = build_quick_task_dialog(
        services,
        projects,
        LIGHT_TOKENS,
        lambda _task: None,
        lambda: None,
    )
    frame = _dialog_frame(dialog, 513)
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "01-default.png", 640, 553)

    _role(dialog, "advanced-toggle")[0].on_click(None)
    frame.height = 757
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "02-advanced-open.png", 640, 797)

    for project_id in (titan.id, overlord.id):
        option = next(item for item in _role(dialog, "project-option") if item.data["project_id"] == project_id)
        option.on_click(None)
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "03-multiple-projects.png", 640, 797)

    stage_fields = _role(dialog, "project-stage")
    for field, stage_id in ((stage_fields[0], titan_stage.id), (stage_fields[1], overlord_stage.id)):
        field.value = str(stage_id)
        field.on_select(None)
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "04-project-stages.png", 640, 797)

    deadline = datetime.combine(date.today() + timedelta(days=5), time(0, 10))
    dialog.data["state"].deadline_at = deadline
    deadline_trigger = _role(dialog, "deadline-trigger")[0]
    deadline_trigger.content.controls[1].value = f"{deadline.day} Aug., {deadline.strftime('%H:%M')}"
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "05-deadline.png", 640, 797)

    _role(dialog, "estimate-hours")[0].value = "4"
    _role(dialog, "estimate-minutes")[0].value = "4"
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "06-estimated-time.png", 640, 797)

    _role(dialog, "checklist-toggle")[0].on_click(None)
    frame.height = 960
    item = _role(dialog, "checklist-item-title")[0]
    item.value = "Define visual acceptance criteria"
    item.on_change(None)
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "07-checklist.png", 640, 1000)

    for _ in range(11):
        _role(dialog, "add-checklist-item")[0].on_click(None)
    for index, field in enumerate(_role(dialog, "checklist-item-title"), start=1):
        field.value = f"Checklist item {index}"
    await _capture(page, screenshot, frame, OUTPUT_ROOT / "08-large-checklist.png", 640, 1000)

    def compose_overlay(include_time: bool) -> ft.Control:
        base = build_quick_task_dialog(
            services,
            projects,
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        picker = build_date_time_picker_dialog(
            LIGHT_TOKENS,
            initial_date=date.today() + timedelta(days=5),
            include_time=include_time,
            initial_time=time(0, 10) if include_time else None,
            first_day_of_week=6,
            on_apply=lambda _value: None,
            close=lambda: None,
        )
        return ft.Stack(
            [
                ft.Container(_dialog_frame(base, 513), left=56, top=86, opacity=0.68),
                ft.Container(
                    width=700,
                    height=640,
                    bgcolor=LIGHT_TOKENS.scrim,
                    opacity=0.20,
                ),
                ft.Container(_overlay_frame(picker), left=85, top=52, width=530, height=430),
            ],
            width=700,
            height=640,
        )

    await _capture(
        page,
        screenshot,
        compose_overlay(False),
        OUTPUT_ROOT / "09-date-picker-overlay.png",
        700,
        640,
    )
    await _capture(
        page,
        screenshot,
        compose_overlay(True),
        OUTPUT_ROOT / "10-deadline-picker-overlay.png",
        700,
        640,
    )
    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

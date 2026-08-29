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
from overlord.modules.tasks.domain import ChecklistItemDraft, TaskDetailsStatus, TaskProjectAssignment
from overlord.ui.components.task_details import build_delete_task_confirmation, build_task_details_dialog
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "task-details"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "task-details-qa.db"


def _dialog_frame(dialog: ft.AlertDialog, height: int) -> ft.Container:
    return ft.Container(
        ft.Column(
            [dialog.title, ft.Container(dialog.content, expand=True), *dialog.actions],
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


def _confirmation_frame(dialog: ft.AlertDialog) -> ft.Container:
    return ft.Container(
        ft.Column(
            [dialog.title, dialog.content, ft.Row(dialog.actions, alignment=ft.MainAxisAlignment.END)],
            spacing=LIGHT_TOKENS.space_4,
            tight=True,
        ),
        width=430,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_large,
        padding=LIGHT_TOKENS.space_5,
    )


async def _capture(page: ft.Page, screenshot: ft.Screenshot, control: ft.Control, path: Path, height: int) -> None:
    page.window.width = 672
    page.window.height = min(height + 72, 1060)
    screenshot.content = ft.Container(
        control,
        width=640,
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
    selected_day = date.today()

    basic = services.tasks.create_task.execute(
        None, "Prepare the weekly review", description="Collect the decisions and open questions.",
        schedule_start_date=selected_day,
    )
    multiple = services.tasks.create_task.execute(
        titan.id, "Coordinate the shared release", schedule_start_date=selected_day,
        deadline_at=datetime.combine(selected_day + timedelta(days=3), time(18, 30)),
        project_links=(TaskProjectAssignment(titan.id), TaskProjectAssignment(overlord.id)),
    )
    stages = services.tasks.create_task.execute(
        titan.id, "Finish Task Details", schedule_start_date=selected_day,
        project_links=(
            TaskProjectAssignment(titan.id, titan_stage.id),
            TaskProjectAssignment(overlord.id, overlord_stage.id),
        ),
    )
    estimated = services.tasks.create_task.execute(
        inbox.id, "Long-term research backlog", schedule_start_date=selected_day, estimate_minutes=9000,
    )
    without_estimate = services.tasks.create_task.execute(
        inbox.id, "Unestimated follow-up", schedule_start_date=selected_day,
    )
    checklist = services.tasks.create_task.execute(
        titan.id, "QA the Task flow", schedule_start_date=selected_day,
        checklist_items=(
            ChecklistItemDraft("Check the header", True),
            ChecklistItemDraft("Verify Project Stages", False, (ChecklistItemDraft("Cross-Project guard", True),)),
            ChecklistItemDraft("Confirm persistence"),
        ),
    )
    large_checklist = services.tasks.create_task.execute(
        overlord.id, "Release checklist", schedule_start_date=selected_day,
        checklist_items=tuple(
            ChecklistItemDraft(f"Release check {index}", index < 4) for index in range(1, 15)
        ),
    )
    paused = services.tasks.create_task.execute(
        titan.id, "Paused while awaiting review", schedule_start_date=selected_day,
    )
    services.tasks.update_details.execute(
        paused.id,
        title=paused.title,
        description=paused.description or "",
        schedule_start_date=paused.schedule_start_date,
        deadline_at=None,
        estimate_minutes=None,
        project_links=(TaskProjectAssignment(titan.id),),
        checklist_items=(),
        status=TaskDetailsStatus.PAUSED,
    )

    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    screenshot = ft.Screenshot(ft.Container())
    page.add(screenshot)

    def details(task_id: int) -> ft.AlertDialog:
        return build_task_details_dialog(
            services, projects, task_id, selected_day, LIGHT_TOKENS,
            lambda: None, lambda: None, print,
        )

    captures = (
        (basic.id, "01-basic-task-details.png", 720),
        (multiple.id, "02-multiple-projects.png", 760),
        (stages.id, "03-project-stage-selectors.png", 810),
        (estimated.id, "04-estimated-time-150h.png", 760),
        (without_estimate.id, "05-without-estimated-time.png", 760),
        (checklist.id, "06-checklist.png", 940),
        (large_checklist.id, "07-large-checklist-scroll.png", 1000),
        (paused.id, "08-paused-status.png", 760),
    )
    for task_id, filename, height in captures:
        await _capture(page, screenshot, _dialog_frame(details(task_id), height), OUTPUT_ROOT / filename, height + 40)

    confirmation = build_delete_task_confirmation(
        services, basic.id, LIGHT_TOKENS,
        close_confirmation=lambda: None, on_deleted=lambda: None, report_error=print,
    )
    delete_composite = ft.Stack(
        [
            ft.Container(_dialog_frame(details(basic.id), 720), left=20, top=20, opacity=0.72),
            ft.Container(width=640, height=780, bgcolor=LIGHT_TOKENS.scrim, opacity=0.22),
            ft.Container(_confirmation_frame(confirmation), left=105, top=235),
        ],
        width=640,
        height=780,
    )
    await _capture(page, screenshot, delete_composite, OUTPUT_ROOT / "09-delete-confirmation.png", 780)
    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

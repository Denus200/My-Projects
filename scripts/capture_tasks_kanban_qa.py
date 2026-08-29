from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.tasks.domain import TaskBoardColumn, TaskProjectAssignment
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.shell.app_shell import AppShell
from overlord.ui.state import AppSessionState, TaskFilterState


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "tasks-kanban"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "tasks-kanban-qa.db"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080


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


async def _capture(page: ft.Page, control: ft.Control, path: Path) -> ft.Screenshot:
    frame = ft.Container(
        control,
        width=VIEWPORT_WIDTH,
        height=VIEWPORT_HEIGHT,
        bgcolor=LIGHT_TOKENS.app_background,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    screenshot = ft.Screenshot(frame)
    page.controls.clear()
    page.add(screenshot)
    page.update()
    await asyncio.sleep(0.8)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await screenshot.capture(pixel_ratio=1.0))
    print(path)
    return screenshot


async def main(page: ft.Page) -> None:
    QA_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    QA_DATABASE.unlink(missing_ok=True)
    services = bootstrap(QA_DATABASE).services
    today = date.today()
    focus = services.projects.create_project.execute("Focus", color="#EF767A")
    growth = services.projects.create_project.execute("Growth", color="#D86BE8")
    systems = services.projects.create_project.execute("Systems", color="#67D5DB")

    planned = [
        services.tasks.create_task.execute(
            focus.id,
            "Sports",
            schedule_start_date=today + timedelta(days=1),
            schedule_start_time=time(17, 0),
        ),
        services.tasks.create_task.execute(
            focus.id,
            "English Classes",
            schedule_start_date=today + timedelta(days=1),
            schedule_start_time=time(19, 0),
            schedule_end_date=today + timedelta(days=1),
            schedule_end_time=time(20, 0),
        ),
        services.tasks.create_task.execute(systems.id, "Prepare research notes"),
    ]
    in_progress = [
        services.tasks.create_task.execute(
            growth.id,
            "Segment customer demographics",
            schedule_start_date=today,
        ),
        services.tasks.create_task.execute(
            growth.id,
            "Analyze open rates",
            schedule_start_date=today,
        ),
        services.tasks.create_task.execute(
            None,
            "A/B test subject lines",
            schedule_start_date=today,
            deadline_at=datetime.combine(today + timedelta(days=2), time(15, 0)),
            project_links=(
                TaskProjectAssignment(systems.id),
                TaskProjectAssignment(growth.id),
            ),
        ),
        services.tasks.create_task.execute(
            systems.id,
            "Optimize send times",
            schedule_start_date=today,
        ),
    ]
    services.tasks.create_task.execute(
        systems.id,
        "Resolve deployment dependency",
        blocker_type=BlockerType.DEPENDENCY,
        blocker_description="Waiting for the local packaging prerequisite.",
    )
    services.tasks.create_task.execute(
        focus.id,
        "Review expired milestone",
        schedule_start_date=today - timedelta(days=2),
        deadline_at=datetime.combine(today - timedelta(days=1), time(18, 0)),
    )
    for title in (
        "Filter email list",
        "Testing screens in the app before sending",
        "English Classes follow-up",
        "Archive sent newsletter",
    ):
        task = services.tasks.create_task.execute(
            focus.id,
            title,
            schedule_start_date=today,
        )
        services.tasks.complete_task.execute(task.id)

    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    page.window.width = VIEWPORT_WIDTH + 16
    page.window.height = 1060

    def build(*, collapsed: bool, filters: TaskFilterState | None = None, state: AppSessionState | None = None) -> ft.Control:
        session = state or AppSessionState(
            route="/tasks",
            sidebar_collapsed=collapsed,
            task_filters=filters,
        )
        shell = AppShell(
            LIGHT_TOKENS,
            "/tasks",
            collapsed,
            lambda _route: None,
            lambda _event: None,
        )
        tasks = build_tasks(
            services,
            LIGHT_TOKENS,
            session,
            lambda: None,
            lambda error: print(error),
            page,
        )
        hosts = _role(tasks, "task-view-host")
        if hosts:
            hosts[0].height = 928
        toolbars = _role(tasks, "tasks-toolbar")
        if toolbars:
            toolbars[0].width = 1816 if collapsed else 1640
        for item in (
            *_role(tasks, "kanban-board"),
            *_role(tasks, "kanban-columns"),
            *_role(tasks, "kanban-column"),
            *_role(tasks, "kanban-column-target"),
            *_role(tasks, "kanban-add-section"),
        ):
            item.height = 928
        shell.set_content(tasks)
        return shell.control

    await _capture(page, build(collapsed=False), OUTPUT_ROOT / "01-expanded-sidebar.png")
    await _capture(page, build(collapsed=True), OUTPUT_ROOT / "02-collapsed-sidebar.png")

    for number in range(12):
        services.tasks.create_task.execute(
            systems.id,
            f"Scrollable work item {number + 1:02d}",
            schedule_start_date=today,
        )
    scroll_control = build(collapsed=False)
    screenshot = await _capture(
        page,
        scroll_control,
        OUTPUT_ROOT / "03-internal-scroll-column.png",
    )
    in_progress_lists = [
        item
        for item in _role(scroll_control, "kanban-column-task-list")
        if item.data["column"] == TaskBoardColumn.IN_PROGRESS.value
    ]
    if in_progress_lists:
        await in_progress_lists[0].scroll_to(offset=360, duration=0)
        page.update()
        await asyncio.sleep(0.3)
        (OUTPUT_ROOT / "03-internal-scroll-column.png").write_bytes(
            await screenshot.capture(pixel_ratio=1.0)
        )

    await _capture(
        page,
        build(
            collapsed=False,
            filters=TaskFilterState(project=str(growth.id)),
        ),
        OUTPUT_ROOT / "04-project-filtered.png",
    )
    await _capture(
        page,
        build(
            collapsed=False,
            filters=TaskFilterState(search="Analyze"),
        ),
        OUTPUT_ROOT / "05-search-filtered.png",
    )

    services.tasks.move_to_board_column.execute(
        planned[0].id,
        TaskBoardColumn.IN_PROGRESS,
    )
    moved_state = AppSessionState(route="/tasks", sidebar_collapsed=False)
    moved_state.task_card_order[TaskBoardColumn.IN_PROGRESS.value] = [
        planned[0].id,
        *(task.id for task in in_progress),
    ]
    await _capture(
        page,
        build(collapsed=False, state=moved_state),
        OUTPUT_ROOT / "06-drag-moved-result.png",
    )

    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

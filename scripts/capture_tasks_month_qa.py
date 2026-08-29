from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.shell.app_shell import AppShell
from overlord.ui.state import AppSessionState, TaskFilterState


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "tasks-month"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "tasks-month-qa.db"
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
    month_start = today.replace(day=1)
    focus = services.projects.create_project.execute("Focus", color="#EF767A")
    growth = services.projects.create_project.execute("Growth", color="#67D5DB")
    systems = services.projects.create_project.execute("Systems", color="#D86BE8")

    first_visible = month_start - timedelta(days=month_start.weekday())
    busy_day = month_start + timedelta(days=3)
    filtered_day = month_start + timedelta(days=8)
    adjacent_day = first_visible if first_visible.month != month_start.month else month_start

    for index, title in enumerate(
        (
            "Filter email list",
            "Segment customer demographics",
            "Analyze open rates",
            "A/B test subject lines",
            "Optimize send times",
            "Review campaign brief",
            "Publish launch checklist",
            "Confirm stakeholder feedback",
            "Prepare metrics summary",
            "Archive test variants",
        )
    ):
        task = services.tasks.create_task.execute(
            focus.id if index < 4 else growth.id,
            title,
            schedule_start_date=busy_day,
        )
        if index < 3:
            services.tasks.complete_task.execute(task.id)
        elif index == 4:
            services.tasks.change_lifecycle.execute(
                task.id,
                TaskLifecycle.PAUSED,
                "Paused for Month QA",
            )
        elif index == 5:
            services.tasks.open_blocker.execute(
                task.id,
                BlockerType.OTHER,
                "Waiting for Month QA input",
            )

    services.tasks.create_task.execute(
        None,
        "Multi-project calendar review",
        schedule_start_date=filtered_day,
        project_links=(
            TaskProjectAssignment(growth.id),
            TaskProjectAssignment(systems.id),
        ),
    )
    services.tasks.create_task.execute(
        focus.id,
        "Plan next campaign",
        schedule_start_date=filtered_day,
    )
    services.tasks.create_task.execute(
        systems.id,
        "Adjacent-month handoff",
        schedule_start_date=adjacent_day,
    )
    if today != busy_day:
        services.tasks.create_task.execute(
            growth.id,
            "Today planning review",
            schedule_start_date=today,
        )

    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    page.window.width = VIEWPORT_WIDTH + 16
    page.window.height = 1060

    def build(
        *,
        collapsed: bool,
        anchor: date = month_start,
        filters: TaskFilterState | None = None,
        expanded_navigation: bool = False,
    ) -> ft.Control:
        session = AppSessionState(
            route="/tasks",
            sidebar_collapsed=collapsed,
            task_filters=filters,
            task_view_mode="month",
            task_calendar_anchor=anchor.isoformat(),
            task_expanded_date_navigation=("month" if expanded_navigation else None),
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
        shell.set_content(tasks)
        return shell.control

    await _capture(page, build(collapsed=False), OUTPUT_ROOT / "01-expanded-sidebar.png")
    await _capture(page, build(collapsed=True), OUTPUT_ROOT / "02-collapsed-sidebar.png")
    await _capture(
        page,
        build(collapsed=False, expanded_navigation=True),
        OUTPUT_ROOT / "03-current-month-with-tasks.png",
    )

    next_month = date(
        month_start.year + (1 if month_start.month == 12 else 0),
        1 if month_start.month == 12 else month_start.month + 1,
        1,
    )
    await _capture(
        page,
        build(collapsed=False, anchor=next_month, expanded_navigation=True),
        OUTPUT_ROOT / "04-next-month-navigation.png",
    )

    busy = build(collapsed=False)
    busy_screenshot = await _capture(
        page,
        busy,
        OUTPUT_ROOT / "05-busy-day-overflow.png",
    )
    busy_lists = [
        item
        for item in _role(busy, "month-day-task-list")
        if item.data.get("day") == busy_day.isoformat()
    ]
    if busy_lists:
        await busy_lists[0].scroll_to(offset=150, duration=0)
        page.update()
        await asyncio.sleep(0.3)
        (OUTPUT_ROOT / "05-busy-day-overflow.png").write_bytes(
            await busy_screenshot.capture(pixel_ratio=1.0)
        )

    await _capture(
        page,
        build(collapsed=False, filters=TaskFilterState(search="calendar")),
        OUTPUT_ROOT / "06-search-filtered.png",
    )
    await _capture(
        page,
        build(
            collapsed=False,
            filters=TaskFilterState(project=str(growth.id)),
        ),
        OUTPUT_ROOT / "07-project-filtered.png",
    )

    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

from __future__ import annotations

import asyncio
import sys
from datetime import date, time, timedelta
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.shell.app_shell import AppShell
from overlord.ui.state import AppSessionState, TaskFilterState


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "tasks-week"
QA_DATABASE = REPOSITORY_ROOT / "data" / "test-tmp" / "tasks-week-qa.db"
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
    week_start = today - timedelta(days=today.weekday())
    focus = services.projects.create_project.execute("Focus", color="#EF767A")
    growth = services.projects.create_project.execute("Growth", color="#D86BE8")
    systems = services.projects.create_project.execute("Systems", color="#67D5DB")

    monday = week_start
    tuesday = week_start + timedelta(days=1)
    wednesday = week_start + timedelta(days=2)
    thursday = week_start + timedelta(days=3)
    friday = week_start + timedelta(days=4)
    saturday = week_start + timedelta(days=5)

    completed_titles = (
        "Sports",
        "English Classes",
        "Segment customer demographics",
        "Analyze open rates",
        "A/B test subject lines",
        "Optimize send times",
    )
    for index, title in enumerate(completed_titles):
        task = services.tasks.create_task.execute(
            focus.id if index < 2 else growth.id,
            title,
            schedule_start_date=monday,
            schedule_start_time=time(17 + index % 3, 0),
        )
        services.tasks.complete_task.execute(task.id)

    services.tasks.create_task.execute(
        focus.id,
        "English Classes",
        schedule_start_date=tuesday,
        schedule_start_time=time(19, 0),
        schedule_end_date=tuesday,
        schedule_end_time=time(20, 0),
    )
    services.tasks.create_task.execute(
        growth.id,
        "Segment customer demographics",
        schedule_start_date=tuesday,
    )
    services.tasks.create_task.execute(
        growth.id,
        "Analyze open rates",
        schedule_start_date=tuesday,
    )
    services.tasks.create_task.execute(
        None,
        "A/B test subject lines",
        schedule_start_date=tuesday,
        project_links=(
            TaskProjectAssignment(systems.id),
            TaskProjectAssignment(growth.id),
        ),
    )
    paused = services.tasks.create_task.execute(
        systems.id,
        "Optimize send times",
        schedule_start_date=tuesday,
    )
    services.tasks.change_lifecycle.execute(
        paused.id,
        TaskLifecycle.PAUSED,
        "Paused for Week QA",
    )

    for day, titles in (
        (wednesday, ("Sports", "English Classes")),
        (thursday, ("English Classes",)),
        (friday, ("Sports", "English Classes")),
        (saturday, ("English Classes",)),
    ):
        for index, title in enumerate(titles):
            services.tasks.create_task.execute(
                focus.id,
                title,
                schedule_start_date=day,
                schedule_start_time=time(17 + index * 2, 0),
            )

    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)
    page.window.width = VIEWPORT_WIDTH + 16
    page.window.height = 1060

    def build(
        *,
        collapsed: bool,
        filters: TaskFilterState | None = None,
        expanded_navigation: bool = False,
    ) -> ft.Control:
        session = AppSessionState(
            route="/tasks",
            sidebar_collapsed=collapsed,
            task_filters=filters,
            task_view_mode="week",
            task_calendar_anchor=week_start.isoformat(),
            task_expanded_date_navigation=("week" if expanded_navigation else None),
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
        for item in (*_role(tasks, "week-board"), *_role(tasks, "week-day-column")):
            item.height = 928
        shell.set_content(tasks)
        return shell.control

    await _capture(page, build(collapsed=False), OUTPUT_ROOT / "01-expanded-sidebar.png")
    await _capture(page, build(collapsed=True), OUTPUT_ROOT / "02-collapsed-sidebar.png")

    later_days = build(collapsed=False)
    later_screenshot = await _capture(
        page,
        later_days,
        OUTPUT_ROOT / "03-horizontal-scroll-later-days.png",
    )
    week_boards = _role(later_days, "week-board")
    if week_boards:
        await week_boards[0].scroll_to(offset=720, duration=0)
        page.update()
        await asyncio.sleep(0.3)
        (OUTPUT_ROOT / "03-horizontal-scroll-later-days.png").write_bytes(
            await later_screenshot.capture(pixel_ratio=1.0)
        )

    for number in range(14):
        services.tasks.create_task.execute(
            systems.id,
            f"Scrollable Tuesday item {number + 1:02d}",
            schedule_start_date=tuesday,
        )
    overflow = build(collapsed=False)
    overflow_screenshot = await _capture(
        page,
        overflow,
        OUTPUT_ROOT / "04-internal-day-scroll.png",
    )
    tuesday_lists = [
        item
        for item in _role(overflow, "week-day-task-list")
        if item.data.get("day") == tuesday.isoformat()
    ]
    if tuesday_lists:
        await tuesday_lists[0].scroll_to(offset=420, duration=0)
        page.update()
        await asyncio.sleep(0.3)
        (OUTPUT_ROOT / "04-internal-day-scroll.png").write_bytes(
            await overflow_screenshot.capture(pixel_ratio=1.0)
        )

    await _capture(
        page,
        build(collapsed=False, filters=TaskFilterState(search="Analyze")),
        OUTPUT_ROOT / "05-search-filtered.png",
    )
    await _capture(
        page,
        build(
            collapsed=False,
            filters=TaskFilterState(project=str(growth.id)),
        ),
        OUTPUT_ROOT / "06-project-filtered.png",
    )
    await _capture(
        page,
        build(collapsed=False, expanded_navigation=True),
        OUTPUT_ROOT / "07-expanded-week-navigation.png",
    )

    QA_DATABASE.unlink(missing_ok=True)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

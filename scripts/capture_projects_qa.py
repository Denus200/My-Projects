from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import flet as ft


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.bootstrap import bootstrap
from overlord.demo import DEMO_DATABASE_PATH, seed_demo_database
from overlord.ui.design_system.themes import build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.projects.page import _project_dialog, build_projects
from overlord.ui.state import AppSessionState


OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "projects"


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


async def _capture(page: ft.Page, control: ft.Control, path: Path, width: int, height: int) -> None:
    page.window.width = width + 16
    page.window.height = min(height + 39, 1060)
    page.update()
    await asyncio.sleep(0.35)
    control.width = width
    control.height = height
    frame = ft.Container(
        control,
        width=width,
        height=height,
        bgcolor=LIGHT_TOKENS.app_background,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    screenshot = ft.Screenshot(frame)
    page.controls.clear()
    page.add(screenshot)
    page.update()
    await asyncio.sleep(0.6)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await screenshot.capture(pixel_ratio=1.0))
    print(path)


async def main(page: ft.Page) -> None:
    seed_demo_database(DEMO_DATABASE_PATH, reset=True)
    services = bootstrap(DEMO_DATABASE_PATH).services
    projects = services.projects.list_projects.execute(search="Overlord")
    if not projects:
        raise RuntimeError("Deterministic demo Project 'Overlord' is missing.")
    project = projects[0]
    linked_projects = services.projects.list_projects.execute(search="Portfolio Refresh")
    if not linked_projects:
        raise RuntimeError("Deterministic demo Project with a linked 12-Week Plan is missing.")
    linked_project = linked_projects[0]
    page.padding = 0
    page.bgcolor = LIGHT_TOKENS.app_background
    page.theme = build_light_theme(motion_enabled=False)

    def build(route: str) -> ft.Control:
        return build_projects(
            services,
            LIGHT_TOKENS,
            route,
            lambda *_: None,
            lambda: None,
            lambda error: print(error),
            AppSessionState(route=route),
            page,
        )

    await _capture(page, build("/projects"), OUTPUT_ROOT / "projects-list-expanded.png", 1688, 941)
    await _capture(page, build("/projects"), OUTPUT_ROOT / "projects-list-collapsed.png", 1864, 941)
    await _capture(page, build(f"/projects/{project.id}"), OUTPUT_ROOT / "project-overview.png", 1688, 941)
    await _capture(page, build(f"/projects/{linked_project.id}"), OUTPUT_ROOT / "project-overview-cycle.png", 1688, 941)
    await _capture(page, build(f"/projects/{project.id}/plan"), OUTPUT_ROOT / "project-plan.png", 1688, 941)
    task_view = build(f"/projects/{project.id}/tasks")
    await _capture(page, task_view, OUTPUT_ROOT / "project-tasks-all.png", 1688, 941)
    filters = _role(task_view, "project-task-filters")[0]
    stage_toggle = filters.controls[0].content.controls[1]
    stage_toggle.on_click(None)
    page.update()
    await asyncio.sleep(0.3)
    screenshot = page.controls[0]
    (OUTPUT_ROOT / "project-tasks-by-stage.png").write_bytes(await screenshot.capture(pixel_ratio=1.0))
    print(OUTPUT_ROOT / "project-tasks-by-stage.png")
    await _capture(page, build(f"/projects/{project.id}/notes"), OUTPUT_ROOT / "project-notes-files.png", 1688, 941)
    await _capture(page, build(f"/projects/{project.id}/archive"), OUTPUT_ROOT / "project-archive.png", 1688, 941)

    dialog = _project_dialog(services, LIGHT_TOKENS, lambda *_: None, lambda: None)
    dialog_preview = ft.Container(
        ft.Column(
            [
                dialog.title if isinstance(dialog.title, ft.Control) else ft.Text(str(dialog.title), color=LIGHT_TOKENS.text_primary, size=LIGHT_TOKENS.text_title, weight=ft.FontWeight.W_700),
                dialog.content,
                ft.Row(dialog.actions or [], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],
            spacing=LIGHT_TOKENS.space_4,
        ),
        width=499,
        height=635,
        bgcolor=LIGHT_TOKENS.surface_elevated,
        border=ft.Border.all(LIGHT_TOKENS.border_width, LIGHT_TOKENS.border_default),
        border_radius=LIGHT_TOKENS.radius_medium,
        padding=LIGHT_TOKENS.space_5,
    )
    await _capture(page, dialog_preview, OUTPUT_ROOT / "create-project.png", 499, 635)
    await page.window.close()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(REPOSITORY_ROOT / "assets"))

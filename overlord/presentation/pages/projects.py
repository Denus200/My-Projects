from __future__ import annotations

import flet as ft

from overlord.application import ApplicationServices
from overlord.domain.projects import ProjectStatus
from overlord.presentation.components.common import card, empty_state, page_heading, state_chip, task_row
from overlord.presentation.design_system.tokens import ThemeTokens


def build_projects(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    refresh,
    report_error,
) -> ft.Control:
    if route.startswith("/projects/"):
        return _build_detail(services, tokens, route, navigate, refresh, report_error)
    title = ft.TextField(label="Project title", expand=True)
    description = ft.TextField(label="Description", multiline=True, min_lines=1, max_lines=3, expand=True)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def create(_event):
        try:
            project = services.projects.create_project.execute(title.value or "", description.value or "")
            navigate(f"/projects/{project.id}")
        except Exception as error:
            message.value = str(error)
            message.update()

    projects = services.projects.list_projects.execute()
    status_colors = {
        ProjectStatus.ACTIVE: tokens.success,
        ProjectStatus.ON_HOLD: tokens.warning,
        ProjectStatus.COMPLETED: tokens.info,
        ProjectStatus.ARCHIVED: tokens.neutral,
    }
    list_column = ft.Column(spacing=tokens.space_3)
    search = ft.TextField(label="Search Projects", expand=True)
    status_filter = ft.Dropdown(
        label="Status",
        value="all",
        options=[ft.DropdownOption("all", "All"), *[
            ft.DropdownOption(value.value, value.value.replace("_", " ").title()) for value in ProjectStatus
        ]],
    )

    def render_list(_event=None):
        selected_status = None if status_filter.value == "all" else ProjectStatus(status_filter.value)
        filtered = services.projects.list_projects.execute(selected_status, search.value or "")
        list_column.controls = [
            ft.Container(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(project.title, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600),
                                ft.Text(project.description or "No description", color=tokens.text_muted, size=tokens.text_small, max_lines=2),
                            ],
                            spacing=tokens.space_1,
                            expand=True,
                        ),
                        state_chip(project.status.value.replace("_", " ").title(), status_colors[project.status], tokens),
                        ft.TextButton("Open", on_click=lambda _e, project_id=project.id: navigate(f"/projects/{project_id}")),
                    ]
                ),
                bgcolor=tokens.surface_inner,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            ) for project in filtered
        ] or [empty_state("No Projects match these filters.", tokens)]

    def update_list(event):
        render_list(event)
        list_column.update()

    search.on_change = update_list
    status_filter.on_select = update_list
    render_list()
    return ft.Column(
        [
            page_heading("Projects", "Independent outcomes and their next actions.", tokens),
            card("Create Project", [ft.Row([title, description]), message, ft.Button("Create project", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=create)], tokens),
            card("All Projects", [ft.Row([search, status_filter]), list_column], tokens),
        ],
        spacing=tokens.space_5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _build_detail(services, tokens, route, navigate, refresh, report_error):
    try:
        project_id = int(route.rsplit("/", 1)[1])
        detail = services.projects.get_detail.execute(project_id)
    except Exception as error:
        return ft.Column([
            page_heading("Project unavailable", str(error), tokens),
            ft.Button("Back to Projects", on_click=lambda _e: navigate("/projects")),
        ])
    project = detail.project
    tasks = services.tasks.list_tasks.execute(project_id=project.id)

    def set_status(status):
        def action(_event):
            try:
                services.projects.update_project.execute(project.id, status=status)
                refresh()
            except Exception as error:
                report_error(str(error))
        return action

    def complete(task_id):
        def action(_event):
            try:
                services.tasks.complete_task.execute(task_id)
                refresh()
            except Exception as error:
                report_error(str(error))
        return action

    progress = detail.completed_task_count / detail.task_count if detail.task_count else 0
    controls = [task_row(item, tokens, on_complete=complete(item.task.id)) for item in tasks]
    return ft.Column(
        [
            page_heading(
                project.title,
                project.description or "Project detail",
                tokens,
                [ft.TextButton("All Projects", on_click=lambda _e: navigate("/projects"))],
            ),
            ft.ResponsiveRow(
                [
                    card("Progress", [
                        ft.Text(f"{detail.completed_task_count} of {detail.task_count} Tasks complete", color=tokens.text_secondary),
                        ft.ProgressBar(value=progress, color=tokens.accent_primary, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
                        ft.Text(f"Open blockers: {detail.open_blocker_count}", color=tokens.text_muted),
                        ft.Text(f"Next action: {detail.next_action or 'Not set'}", color=tokens.text_muted),
                        ft.Text("Actual time: Not tracked yet", color=tokens.text_muted),
                    ], tokens, col={"sm": 12, "lg": 5}),
                    card("Lifecycle", [
                        ft.Text(f"Current status: {project.status.value.replace('_', ' ').title()}", color=tokens.text_primary),
                        ft.Row([
                            ft.TextButton("Active", on_click=set_status(ProjectStatus.ACTIVE)),
                            ft.TextButton("On hold", on_click=set_status(ProjectStatus.ON_HOLD)),
                            ft.TextButton("Complete", on_click=set_status(ProjectStatus.COMPLETED)),
                            ft.TextButton("Archive", on_click=set_status(ProjectStatus.ARCHIVED)),
                        ], wrap=True),
                    ], tokens, col={"sm": 12, "lg": 7}),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
            card("Project Tasks", controls or [empty_state("This Project has no Tasks yet.", tokens, ft.Button("Create Task", on_click=lambda _e: navigate("/tasks")))], tokens),
        ],
        spacing=tokens.space_5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

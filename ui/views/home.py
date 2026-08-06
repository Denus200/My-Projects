from datetime import date

import flet as ft

from core.statuses import task_status_values
from ui.style.theme import AppStyle


def home_view(page: ft.Page, today_service, project_service):
    task_list = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
    feedback = ft.Text("", color=AppStyle.WARNING, size=13)

    project_dropdown = ft.Dropdown(
        label="Project",
        width=260,
        bgcolor=AppStyle.BG_SIDEBAR,
        border_color=AppStyle.PRIMARY,
    )
    new_project_title = ft.TextField(
        label="New project",
        width=260,
        bgcolor=AppStyle.BG_SIDEBAR,
        border_color=AppStyle.TEXT_MUTED,
    )
    task_title = ft.TextField(
        label="Task for today",
        expand=True,
        bgcolor=AppStyle.BG_SIDEBAR,
        border_color=AppStyle.PRIMARY,
    )
    planned_minutes = ft.TextField(
        label="Min",
        width=90,
        bgcolor=AppStyle.BG_SIDEBAR,
        border_color=AppStyle.TEXT_MUTED,
    )

    def set_feedback(message: str, color: str = AppStyle.WARNING):
        feedback.value = message
        feedback.color = color

    def load_projects():
        projects = project_service.list_active_projects()
        project_dropdown.options = [
            ft.dropdown.Option(key=str(project.id), text=project.title)
            for project in projects
        ]
        if projects and not project_dropdown.value:
            project_dropdown.value = str(projects[0].id)

    def parse_minutes():
        value = planned_minutes.value.strip()
        if not value:
            return None
        try:
            minutes = int(value)
        except ValueError as error:
            raise ValueError("Minutes must be a number.") from error
        if minutes <= 0:
            raise ValueError("Minutes must be greater than zero.")
        return minutes

    def refresh_tasks():
        task_list.controls.clear()
        tasks = today_service.get_today_tasks()
        if not tasks:
            task_list.controls.append(
                ft.Container(
                    bgcolor=AppStyle.BG_SIDEBAR,
                    border_radius=AppStyle.RADIUS,
                    padding=24,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.TASK_ALT, color=AppStyle.PRIMARY, size=34),
                            ft.Text("No focus tasks for today", size=18, weight="bold", color=AppStyle.TEXT_MAIN),
                            ft.Text("Create one to start the day with a clear next action.", color=AppStyle.TEXT_MUTED),
                        ],
                    ),
                )
            )
            return

        for task in tasks:
            status_dropdown = ft.Dropdown(
                value=task.status,
                width=170,
                options=[ft.dropdown.Option(status) for status in task_status_values()],
                bgcolor=AppStyle.BG_MAIN,
                border_color=AppStyle.TEXT_MUTED,
            )
            comment_field = ft.TextField(
                value=task.comment,
                label="Comment",
                multiline=True,
                min_lines=1,
                max_lines=3,
                expand=True,
                bgcolor=AppStyle.BG_MAIN,
                border_color=AppStyle.TEXT_MUTED,
            )

            def save_task(_, task_id=task.id, status_control=status_dropdown, comment_control=comment_field):
                try:
                    today_service.update_task_state(task_id, status_control.value, comment_control.value)
                    set_feedback("Saved.", AppStyle.SUCCESS)
                    refresh_tasks()
                except ValueError as error:
                    set_feedback(str(error), AppStyle.DANGER)
                page.update()

            task_list.controls.append(
                ft.Container(
                    bgcolor=AppStyle.BG_SIDEBAR,
                    border_radius=AppStyle.RADIUS,
                    padding=18,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=4,
                                        expand=True,
                                        controls=[
                                            ft.Text(task.project_title, color=AppStyle.PRIMARY, size=12),
                                            ft.Text(task.title, color=AppStyle.TEXT_MAIN, size=18, weight="bold"),
                                        ],
                                    ),
                                    ft.Text(f"{task.planned_minutes or '-'} min", color=AppStyle.TEXT_MUTED),
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    status_dropdown,
                                    comment_field,
                                    ft.IconButton(
                                        icon=ft.Icons.SAVE,
                                        icon_color=AppStyle.PRIMARY,
                                        tooltip="Save task state",
                                        on_click=save_task,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                        ],
                    ),
                )
            )

    def add_task(_):
        try:
            project_id = int(project_dropdown.value) if project_dropdown.value else None
            if project_id is None:
                project = project_service.create_project(new_project_title.value)
                project_id = project.id
            today_service.create_task(
                project_id=project_id,
                title=task_title.value,
                scheduled_date=date.today(),
                planned_minutes=parse_minutes(),
            )
            task_title.value = ""
            planned_minutes.value = ""
            new_project_title.value = ""
            project_dropdown.value = None
            load_projects()
            refresh_tasks()
            set_feedback("Task added.", AppStyle.SUCCESS)
        except ValueError as error:
            set_feedback(str(error), AppStyle.DANGER)
        page.update()

    load_projects()
    refresh_tasks()

    return ft.Container(
        padding=36,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=18,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text("Today", size=AppStyle.TITLE_SIZE, color=AppStyle.PRIMARY, weight="bold"),
                                ft.Text("Pick 1-3 project tasks and move them forward.", color=AppStyle.TEXT_MAIN),
                            ],
                        ),
                        ft.Text(date.today().isoformat(), color=AppStyle.TEXT_MUTED),
                    ],
                ),
                ft.Container(
                    bgcolor=AppStyle.SURFACE,
                    border_radius=AppStyle.RADIUS,
                    padding=16,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row([project_dropdown, new_project_title], wrap=True),
                            ft.Row(
                                controls=[
                                    task_title,
                                    planned_minutes,
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_TASK,
                                        icon_color=AppStyle.PRIMARY,
                                        tooltip="Add task for today",
                                        on_click=add_task,
                                    ),
                                ],
                            ),
                            feedback,
                        ],
                    ),
                ),
                task_list,
            ],
        ),
    )

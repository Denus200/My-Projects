from __future__ import annotations

import asyncio
from datetime import date
from typing import Callable

import flet as ft

from overlord.application import ApplicationServices
from overlord.domain.projects import Project
from overlord.domain.tasks import BlockerType, Task, TaskLifecycle
from overlord.presentation.components.common import (
    card,
    dialog_footer,
    empty_state,
    page_heading,
    show_success,
    task_row,
)
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.tokens import ThemeTokens
from overlord.presentation.state import AppSessionState, TaskFilterState
from overlord.presentation.strings import ui_text


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(ui_text("tasks.date_error")) from error


def _project_options(projects: tuple[Project, ...]) -> list[ft.DropdownOption]:
    return [
        ft.DropdownOption("none", ui_text("tasks.no_project")),
        *[ft.DropdownOption(str(item.id), item.title) for item in projects],
    ]


def _project_id(value: str | None) -> int | None:
    return None if value in {None, "none"} else int(value)


def build_quick_task_dialog(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    tokens: ThemeTokens,
    on_created: Callable[[Task], None],
    close: Callable[[], None],
    selected_project_id: int | None = None,
) -> ft.AlertDialog:
    title = ft.TextField(label=ui_text("tasks.field_title"), autofocus=True)
    project = ft.Dropdown(
        label=ui_text("tasks.field_project"),
        value=str(selected_project_id) if selected_project_id is not None else "none",
        options=_project_options(projects),
    )
    planned_date = ft.TextField(
        label=ui_text("tasks.field_planned_date"),
        hint_text="YYYY-MM-DD",
    )
    estimate = ft.TextField(
        label=ui_text("tasks.field_estimate"),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    importance = ft.Checkbox(label=ui_text("tasks.important"), value=False)
    urgency = ft.Checkbox(label=ui_text("tasks.urgent"), value=False)
    definition = ft.TextField(
        label=ui_text("tasks.field_definition"),
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    next_action = ft.TextField(label=ui_text("tasks.field_next_action"))
    blocker_type = ft.Dropdown(
        label=ui_text("tasks.field_blocker_type"),
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, value.value.title()) for value in BlockerType],
    )
    blocker_description = ft.TextField(
        label=ui_text("tasks.field_blocker_description"),
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)
    details = ft.Container(
        ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(planned_date, col={"sm": 12, "md": 7}),
                        ft.Container(estimate, col={"sm": 12, "md": 5}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_3,
                ),
                ft.Row([importance, urgency], wrap=True),
                definition,
                next_action,
                ft.ResponsiveRow(
                    [
                        ft.Container(blocker_type, col={"sm": 12, "md": 5}),
                        ft.Container(blocker_description, col={"sm": 12, "md": 7}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_3,
                ),
            ],
            spacing=tokens.space_3,
        ),
        visible=False,
    )
    details_label = ft.Text(ui_text("tasks.more_details"), color=tokens.accent_primary)

    def toggle_details(_event) -> None:
        details.visible = not details.visible
        details_label.value = ui_text("tasks.fewer_details") if details.visible else ui_text("tasks.more_details")
        details.update()
        details_label.update()

    def create(_event) -> None:
        title.error = None
        planned_date.error = None
        estimate.error = None
        blocker_description.error = None
        message.value = ""
        try:
            chosen_date = _date_value(planned_date.value or "") if (planned_date.value or "").strip() else None
            try:
                minutes = int(estimate.value) if (estimate.value or "").strip() else None
            except ValueError as error:
                raise ValueError(ui_text("tasks.estimate_integer_error")) from error
            blocker_text = (blocker_description.value or "").strip()
            task = services.tasks.create_task.execute(
                _project_id(project.value),
                title.value or "",
                planned_date=chosen_date,
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=True if importance.value else None,
                urgency=True if urgency.value else None,
                estimate_minutes=minutes,
                blocker_type=BlockerType(blocker_type.value) if blocker_text else None,
                blocker_description=blocker_text or None,
            )
            on_created(task)
        except Exception as error:
            text = str(error)
            if "title" in text.lower():
                title.error = text
                title.update()
            elif "estimate" in text.lower():
                estimate.error = text
                estimate.update()
            elif "blocker" in text.lower():
                blocker_description.error = text
                blocker_description.update()
            elif "date" in text.lower():
                planned_date.error = text
                planned_date.update()
            else:
                message.value = text
                message.update()

    return ft.AlertDialog(
        modal=True,
        title=ui_text("tasks.quick_title"),
        content=ft.Container(
            ft.Column(
                [
                    ft.Text(ui_text("tasks.quick_description"), color=tokens.text_secondary),
                    title,
                    project,
                    ft.TextButton(details_label, on_click=toggle_details),
                    details,
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=620,
        ),
        actions=dialog_footer(
            ui_text("tasks.cancel"),
            ui_text("tasks.create"),
            lambda _e: close(),
            create,
            tokens,
        ),
        bgcolor=tokens.surface_elevated,
        scrollable=True,
    )


def build_task_editor_content(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    task_id: int,
    tokens: ThemeTokens,
    on_saved: Callable[[], None],
    on_changed: Callable[[], None],
    close: Callable[[], None],
    report_error,
) -> ft.Control:
    data = services.tasks.get_editor.execute(task_id)
    task = data.task
    project = ft.Dropdown(
        label=ui_text("tasks.field_project"),
        value=str(task.project_id) if task.project_id is not None else "none",
        options=_project_options(projects),
    )
    title = ft.TextField(label=ui_text("tasks.field_title"), value=task.title)
    description = ft.TextField(label=ui_text("tasks.field_description"), value=task.description or "", multiline=True, min_lines=2, max_lines=4)
    definition = ft.TextField(label=ui_text("tasks.field_definition"), value=task.definition_of_done or "", multiline=True, min_lines=2, max_lines=4)
    next_action = ft.TextField(label=ui_text("tasks.field_next_action"), value=task.next_action or "")
    estimate = ft.TextField(label=ui_text("tasks.field_estimate"), value=str(task.estimate_minutes or ""), keyboard_type=ft.KeyboardType.NUMBER)
    importance = ft.Checkbox(label=ui_text("tasks.important"), value=task.importance is True)
    urgency = ft.Checkbox(label=ui_text("tasks.urgent"), value=task.urgency is True)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event) -> None:
        title.error = None
        estimate.error = None
        try:
            minutes = int(estimate.value) if (estimate.value or "").strip() else None
            services.tasks.update_task.execute(
                task.id,
                project_id=_project_id(project.value),
                title=title.value or "",
                description=description.value or "",
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=True if importance.value else None,
                urgency=True if urgency.value else None,
                estimate_minutes=minutes,
            )
            on_saved()
        except Exception as error:
            text = str(error)
            if "title" in text.lower():
                title.error = text
                title.update()
            elif "estimate" in text.lower():
                estimate.error = text
                estimate.update()
            else:
                message.value = text
                message.update()

    lifecycle_buttons = [
        ft.TextButton(
            lifecycle.value.replace("_", " ").title(),
            on_click=lambda _e, value=lifecycle: _change_lifecycle(services, task.id, value, on_changed, report_error),
            disabled=task.lifecycle_status is lifecycle,
        )
        for lifecycle in TaskLifecycle
    ]
    blocker_type = ft.Dropdown(
        label=ui_text("tasks.field_blocker_type"),
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, value.value.title()) for value in BlockerType],
    )
    blocker_description = ft.TextField(label=ui_text("tasks.field_blocker_description"), expand=True)

    def add_blocker(_event) -> None:
        try:
            services.tasks.open_blocker.execute(task.id, BlockerType(blocker_type.value), blocker_description.value or "")
            on_changed()
        except Exception as error:
            blocker_description.error = str(error)
            blocker_description.update()

    blocker_controls: list[ft.Control] = [
        ft.ResponsiveRow(
            [
                ft.Container(blocker_type, col={"sm": 12, "md": 4}),
                ft.Container(blocker_description, col={"sm": 12, "md": 6}),
                ft.Container(ft.Button(ui_text("tasks.open_blocker"), on_click=add_blocker), col={"sm": 12, "md": 2}),
            ],
            spacing=tokens.space_2,
            run_spacing=tokens.space_2,
        )
    ]
    for blocker in data.blockers:
        resolution = ft.TextField(label=ui_text("tasks.resolution"), expand=True)
        if blocker.resolved_at:
            blocker_controls.append(ft.Text(f"{ui_text('tasks.resolved')} · {blocker.description} · {blocker.resolution}", color=tokens.text_muted))
        else:
            blocker_controls.append(
                ft.Container(
                    ft.Column(
                        [
                            ft.Text(f"{blocker.type.value.title()} · {blocker.description}", color=tokens.blocker.text),
                            ft.Row(
                                [
                                    resolution,
                                    ft.Button(
                                        ui_text("tasks.resolve"),
                                        on_click=lambda _e, blocker_id=blocker.id, field=resolution: _resolve_blocker(
                                            services, blocker_id, field.value or "", on_changed, report_error
                                        ),
                                    ),
                                ]
                            ),
                        ]
                    ),
                    bgcolor=tokens.blocker.background,
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )
    plan_history = [
        ft.Text(
            f"{plan.planned_date.isoformat()} · {(plan.today_group.value.title() + ' ' + str(plan.position)) if plan.today_group else ui_text('tasks.no_today_slot')}"
            + (f" · {ui_text('tasks.plan_moved')}" if plan.supersedes_plan_id else f" · {ui_text('tasks.plan_original')}"),
            color=tokens.text_muted,
            size=tokens.text_small,
        )
        for plan in data.planning_history
    ]
    status_history = [
        ft.Text(
            f"{entry.from_status or ui_text('tasks.status_unset')} → {entry.to_status} · {entry.reason or ui_text('tasks.no_reason')}",
            color=tokens.text_muted,
            size=tokens.text_small,
        )
        for entry in data.status_history
    ]
    return ft.Column(
        [
            project,
            title,
            description,
            definition,
            next_action,
            ft.ResponsiveRow(
                [
                    ft.Container(estimate, col={"sm": 12, "md": 4}),
                    ft.Container(importance, col={"sm": 6, "md": 4}),
                    ft.Container(urgency, col={"sm": 6, "md": 4}),
                ]
            ),
            message,
            ft.Text(ui_text("tasks.lifecycle_section"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            ft.Row(lifecycle_buttons, wrap=True),
            ft.Text(ui_text("tasks.blockers_section"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *blocker_controls,
            ft.Text(ui_text("tasks.planning_history"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *(plan_history or [ft.Text(ui_text("tasks.no_planning_history"), color=tokens.text_muted)]),
            ft.Text(ui_text("tasks.status_history"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *(status_history or [ft.Text(ui_text("tasks.no_status_history"), color=tokens.text_muted)]),
            ft.Row(
                [
                    ft.Button(ui_text("tasks.save"), bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=save),
                    ft.TextButton(ui_text("tasks.close"), on_click=lambda _e: close()),
                ]
            ),
        ],
        spacing=tokens.space_3,
        tight=True,
    )


def _change_lifecycle(services, task_id, lifecycle, refresh, report_error) -> None:
    try:
        services.tasks.change_lifecycle.execute(task_id, lifecycle, "Changed in Task editor")
        refresh()
    except Exception as error:
        report_error(str(error))


def _resolve_blocker(services, blocker_id, resolution, refresh, report_error) -> None:
    try:
        services.tasks.resolve_blocker.execute(blocker_id, resolution)
        refresh()
    except Exception as error:
        report_error(str(error))


def build_tasks(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None = None,
) -> ft.Control:
    projects = services.projects.list_projects.execute()
    filter_state = state.task_filters or TaskFilterState()
    state.task_filters = filter_state

    search = ft.TextField(label=ui_text("tasks.search"), value=filter_state.search, expand=True)
    filter_project = ft.Dropdown(
        label=ui_text("tasks.project_filter"),
        value=filter_state.project,
        options=[
            ft.DropdownOption("all", ui_text("tasks.project_all")),
            ft.DropdownOption("none", ui_text("tasks.no_project")),
            *[ft.DropdownOption(str(item.id), item.title) for item in projects],
        ],
    )
    lifecycle = ft.Dropdown(
        label=ui_text("tasks.lifecycle"),
        value=filter_state.lifecycle,
        options=[
            ft.DropdownOption("all", ui_text("tasks.lifecycle_all")),
            *[ft.DropdownOption(value.value, value.value.replace("_", " ").title()) for value in TaskLifecycle],
        ],
    )
    date_scope = ft.Dropdown(
        label=ui_text("tasks.date_scope"),
        value=filter_state.date_scope,
        options=[
            ft.DropdownOption("any", ui_text("tasks.date_any")),
            ft.DropdownOption("today", ui_text("tasks.date_today")),
            ft.DropdownOption("this_week", ui_text("tasks.date_week")),
            ft.DropdownOption("overdue", ui_text("tasks.date_overdue")),
            ft.DropdownOption("unplanned", ui_text("tasks.date_unplanned")),
        ],
    )
    filter_importance = ft.Dropdown(
        label=ui_text("tasks.importance"),
        value=filter_state.importance,
        options=[
            ft.DropdownOption("any", ui_text("tasks.any")),
            ft.DropdownOption("yes", ui_text("tasks.important")),
            ft.DropdownOption("no", ui_text("tasks.not_important")),
        ],
    )
    filter_urgency = ft.Dropdown(
        label=ui_text("tasks.urgency"),
        value=filter_state.urgency,
        options=[
            ft.DropdownOption("any", ui_text("tasks.any")),
            ft.DropdownOption("yes", ui_text("tasks.urgent")),
            ft.DropdownOption("no", ui_text("tasks.not_urgent")),
        ],
    )
    attention_only = ft.Switch(label=ui_text("tasks.attention"), value=filter_state.attention_only)
    result_count = ft.Text("", color=tokens.text_muted, size=tokens.text_small)
    list_column = ft.Column(spacing=tokens.space_2)

    def remember_filters() -> None:
        filter_state.search = search.value or ""
        filter_state.project = filter_project.value or "all"
        filter_state.lifecycle = lifecycle.value or "all"
        filter_state.date_scope = date_scope.value or "any"
        filter_state.importance = filter_importance.value or "any"
        filter_state.urgency = filter_urgency.value or "any"
        filter_state.attention_only = bool(attention_only.value)

    def query_filters() -> dict[str, object]:
        remember_filters()
        filters: dict[str, object] = {"search": filter_state.search}
        if filter_state.project == "none":
            filters["without_project"] = True
        elif filter_state.project != "all":
            filters["project_id"] = int(filter_state.project)
        if filter_state.lifecycle != "all":
            filters["lifecycle"] = TaskLifecycle(filter_state.lifecycle)
        if filter_state.date_scope != "any":
            filters["date_scope"] = filter_state.date_scope
            filters["reference_date"] = date.today()
        if filter_state.importance != "any":
            filters["importance"] = filter_state.importance == "yes"
        if filter_state.urgency != "any":
            filters["urgency"] = filter_state.urgency == "yes"
        if filter_state.attention_only:
            filters["attention_only"] = True
        return filters

    def close_dialog() -> None:
        if page is not None:
            page.pop_dialog()

    def render_list(_event=None, *, update: bool = False) -> None:
        matches = services.tasks.list_tasks.execute(**query_filters())
        task_controls: list[ft.Control] = []
        for item in matches:
            def edit(_event, task_id=item.task.id) -> None:
                open_editor(task_id)

            def complete(_event, task_id=item.task.id) -> None:
                try:
                    services.tasks.complete_task.execute(task_id)
                    render_list(update=True)
                except Exception as error:
                    report_error(str(error))

            task_controls.append(task_row(item, tokens, on_complete=complete, on_edit=edit))
        list_column.controls = task_controls or [empty_state(ui_text("tasks.empty"), tokens)]
        result_count.value = ui_text("tasks.results_count", count=len(matches))
        if update:
            list_column.update()
            result_count.update()

    def created(_task: Task) -> None:
        close_dialog()
        render_list(update=True)
        if page is not None:
            show_success(page, tokens, ui_text("tasks.created"))

    def open_quick_task(_event) -> None:
        if page is None:
            return
        page.show_dialog(build_quick_task_dialog(services, projects, tokens, created, close_dialog))

    def open_editor(task_id: int) -> None:
        if page is None:
            return

        def saved() -> None:
            close_dialog()
            render_list(update=True)
            show_success(page, tokens, ui_text("tasks.updated"))

        def changed() -> None:
            close_dialog()
            render_list(update=True)
            open_editor(task_id)

        dialog = ft.AlertDialog(
            modal=True,
            title=ui_text("tasks.edit_title"),
            content=ft.Container(
                build_task_editor_content(
                    services,
                    projects,
                    task_id,
                    tokens,
                    saved,
                    changed,
                    close_dialog,
                    report_error,
                ),
                width=680,
            ),
            bgcolor=tokens.surface_elevated,
            scrollable=True,
        )
        page.show_dialog(dialog)

    def apply_filters(_event) -> None:
        try:
            render_list(update=True)
        except Exception as error:
            report_error(str(error))

    def reset_filters(_event) -> None:
        search.value = ""
        filter_project.value = "all"
        lifecycle.value = "all"
        date_scope.value = "any"
        filter_importance.value = "any"
        filter_urgency.value = "any"
        attention_only.value = False
        for control in (search, filter_project, lifecycle, date_scope, filter_importance, filter_urgency, attention_only):
            control.update()
        render_list(update=True)

    search.on_submit = apply_filters
    render_list()
    content = ft.Column(
        [
            page_heading(
                ui_text("tasks.title"),
                ui_text("tasks.subtitle"),
                tokens,
                [
                    ft.Button(
                        ft.Row(
                            [
                                lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("tasks.quick_action")),
                                ft.Text(ui_text("tasks.quick_action"), color=tokens.on_accent),
                            ],
                            spacing=tokens.space_2,
                            tight=True,
                        ),
                        bgcolor=tokens.accent_primary,
                        color=tokens.on_accent,
                        elevation=0,
                        on_click=open_quick_task,
                    )
                ],
            ),
            card(
                ui_text("tasks.results"),
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(search, col={"sm": 12, "lg": 5}),
                            ft.Container(filter_project, col={"sm": 12, "md": 6, "lg": 3}),
                            ft.Container(lifecycle, col={"sm": 12, "md": 6, "lg": 4}),
                            ft.Container(date_scope, col={"sm": 12, "md": 4}),
                            ft.Container(filter_importance, col={"sm": 12, "md": 4}),
                            ft.Container(filter_urgency, col={"sm": 12, "md": 4}),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_3,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(attention_only, col={"sm": 12, "md": 6}),
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.TextButton(ui_text("tasks.reset_filters"), on_click=reset_filters),
                                        ft.Button(ui_text("tasks.apply_filters"), on_click=apply_filters),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                                col={"sm": 12, "md": 6},
                            ),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_2,
                    ),
                    result_count,
                    list_column,
                ],
                tokens,
            ),
        ],
        spacing=tokens.space_5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    if state.selected_task_id is not None and page is not None and hasattr(page, "run_task"):
        selected_task_id = state.selected_task_id
        state.selected_task_id = None

        async def open_selected_editor() -> None:
            await asyncio.sleep(0)
            open_editor(selected_task_id)

        page.run_task(open_selected_editor)
    return content

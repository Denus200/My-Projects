from __future__ import annotations

from datetime import date

import flet as ft

from overlord.application import ApplicationServices
from overlord.domain.tasks import BlockerType, TaskLifecycle, TodayGroup
from overlord.presentation.components.common import card, empty_state, page_heading, task_row
from overlord.presentation.design_system.tokens import ThemeTokens
from overlord.presentation.state import AppSessionState


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError("Date must use YYYY-MM-DD.") from error


def build_task_editor_content(
    services: ApplicationServices,
    task_id: int,
    tokens: ThemeTokens,
    refresh,
    close,
    report_error,
) -> ft.Control:
    data = services.tasks.get_editor.execute(task_id)
    task = data.task
    current_plan = data.planning_history[-1] if data.planning_history else None
    title = ft.TextField(label="Title", value=task.title)
    description = ft.TextField(label="Description", value=task.description or "", multiline=True, min_lines=2, max_lines=4)
    definition = ft.TextField(label="Definition of Done", value=task.definition_of_done or "", multiline=True, min_lines=2, max_lines=4)
    next_action = ft.TextField(label="Next action", value=task.next_action or "")
    estimate = ft.TextField(label="Estimate (minutes)", value=str(task.estimate_minutes or ""), keyboard_type=ft.KeyboardType.NUMBER)
    importance = ft.Checkbox(label="Important", value=task.importance is True)
    urgency = ft.Checkbox(label="Urgent", value=task.urgency is True)
    plan_date = ft.TextField(label="Planned date", value=current_plan.planned_date.isoformat() if current_plan else date.today().isoformat())
    group = ft.Dropdown(
        label="Today group",
        value=current_plan.today_group.value if current_plan and current_plan.today_group else "none",
        options=[ft.DropdownOption("none", "No Dashboard slot"), ft.DropdownOption("primary", "Primary"), ft.DropdownOption("secondary", "Secondary")],
    )
    position = ft.Dropdown(
        label="Position",
        value=str(current_plan.position) if current_plan and current_plan.position else "none",
        options=[ft.DropdownOption("none", "No position"), *[ft.DropdownOption(str(number), str(number)) for number in range(1, 5)]],
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event):
        try:
            minutes = int(estimate.value) if (estimate.value or "").strip() else None
            services.tasks.update_task.execute(
                task.id,
                title=title.value or "",
                description=description.value or "",
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=importance.value,
                urgency=urgency.value,
                estimate_minutes=minutes,
            )
            chosen_group = None if group.value == "none" else TodayGroup(group.value)
            chosen_position = None if position.value == "none" else int(position.value)
            services.tasks.assign_plan.execute(task.id, _date_value(plan_date.value or ""), chosen_group, chosen_position)
            refresh()
        except Exception as error:
            message.value = str(error)
            message.update()

    lifecycle_buttons = []
    for lifecycle in TaskLifecycle:
        lifecycle_buttons.append(
            ft.TextButton(
                lifecycle.value.replace("_", " ").title(),
                on_click=lambda _e, value=lifecycle: _change_lifecycle(services, task.id, value, refresh, report_error),
                disabled=task.lifecycle_status is lifecycle,
            )
        )
    blocker_type = ft.Dropdown(
        label="Blocker type",
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, value.value.title()) for value in BlockerType],
    )
    blocker_description = ft.TextField(label="Blocker description", expand=True)

    def add_blocker(_event):
        try:
            services.tasks.open_blocker.execute(task.id, BlockerType(blocker_type.value), blocker_description.value or "")
            refresh()
        except Exception as error:
            report_error(str(error))

    blocker_controls: list[ft.Control] = [ft.Row([blocker_type, blocker_description, ft.Button("Open blocker", on_click=add_blocker)])]
    for blocker in data.blockers:
        resolution = ft.TextField(label="Resolution", expand=True)
        if blocker.resolved_at:
            blocker_controls.append(ft.Text(f"Resolved · {blocker.description} · {blocker.resolution}", color=tokens.text_muted))
        else:
            blocker_controls.append(
                ft.Container(
                    ft.Column([
                        ft.Text(f"{blocker.type.value.title()} · {blocker.description}", color=tokens.blocker.text),
                        ft.Row([
                            resolution,
                            ft.Button(
                                "Resolve",
                                on_click=lambda _e, blocker_id=blocker.id, field=resolution: _resolve_blocker(
                                    services, blocker_id, field.value or "", refresh, report_error
                                ),
                            ),
                        ]),
                    ]),
                    bgcolor=tokens.blocker.background,
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )
    plan_history = [
        ft.Text(
            f"{plan.planned_date.isoformat()} · {(plan.today_group.value.title() + ' ' + str(plan.position)) if plan.today_group else 'No slot'}"
            + (" · moved" if plan.supersedes_plan_id else " · original"),
            color=tokens.text_muted,
            size=tokens.text_small,
        )
        for plan in data.planning_history
    ]
    status_history = [
        ft.Text(
            f"{entry.from_status or 'unset'} → {entry.to_status} · {entry.reason or 'No reason'}",
            color=tokens.text_muted,
            size=tokens.text_small,
        )
        for entry in data.status_history
    ]
    return card(
        "Task Editor Content",
        [
            ft.Text("Reusable content; no permanent dialog/panel/page shell has been selected.", color=tokens.text_muted, size=tokens.text_small),
            title, description, definition, next_action,
            ft.ResponsiveRow([ft.Container(estimate, col={"sm": 12, "md": 4}), ft.Container(importance, col={"sm": 6, "md": 4}), ft.Container(urgency, col={"sm": 6, "md": 4})]),
            ft.ResponsiveRow([ft.Container(plan_date, col={"sm": 12, "md": 4}), ft.Container(group, col={"sm": 12, "md": 4}), ft.Container(position, col={"sm": 12, "md": 4})]),
            ft.Row([ft.Button("Save changes", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=save), ft.TextButton("Close editor", on_click=close)]),
            message,
            ft.Text("Lifecycle", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            ft.Row(lifecycle_buttons, wrap=True),
            ft.Text("Blockers", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *blocker_controls,
            ft.Text("Planning history", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *(plan_history or [ft.Text("No planning history", color=tokens.text_muted)]),
            ft.Text("Status history", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *(status_history or [ft.Text("No status changes yet", color=tokens.text_muted)]),
        ],
        tokens,
    )


def _change_lifecycle(services, task_id, lifecycle, refresh, report_error):
    try:
        services.tasks.change_lifecycle.execute(task_id, lifecycle, "Changed in Task editor")
        refresh()
    except Exception as error:
        report_error(str(error))


def _resolve_blocker(services, blocker_id, resolution, refresh, report_error):
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
) -> ft.Control:
    projects = services.projects.list_projects.execute()
    project = ft.Dropdown(
        label="Existing Project",
        value=str(projects[0].id) if projects else None,
        options=[ft.DropdownOption(str(item.id), item.title) for item in projects],
        disabled=not projects,
    )
    title = ft.TextField(label="Task title")
    planned_date = ft.TextField(label="Planned date", value=date.today().isoformat())
    definition = ft.TextField(label="Definition of Done", multiline=True, min_lines=1, max_lines=3)
    next_action = ft.TextField(label="Next action")
    group = ft.Dropdown(
        label="Dashboard slot",
        value="none",
        options=[ft.DropdownOption("none", "No slot"), ft.DropdownOption("primary", "Primary"), ft.DropdownOption("secondary", "Secondary")],
    )
    position = ft.Dropdown(
        label="Position",
        value="none",
        options=[ft.DropdownOption("none", "No position"), *[ft.DropdownOption(str(number), str(number)) for number in range(1, 5)]],
    )
    importance = ft.Checkbox(label="Important")
    urgency = ft.Checkbox(label="Urgent")
    create_message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def create(_event):
        try:
            if project.value is None:
                raise ValueError("Create a Project before creating a Task.")
            chosen_group = None if group.value == "none" else TodayGroup(group.value)
            chosen_position = None if position.value == "none" else int(position.value)
            services.tasks.create_task.execute(
                int(project.value),
                title.value or "",
                planned_date=_date_value(planned_date.value or ""),
                today_group=chosen_group,
                position=chosen_position,
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=importance.value,
                urgency=urgency.value,
            )
            refresh()
        except Exception as error:
            create_message.value = str(error)
            create_message.update()

    search = ft.TextField(label="Search title or Project", expand=True)
    filter_project = ft.Dropdown(
        label="Project",
        value="all",
        options=[ft.DropdownOption("all", "All Projects"), *[ft.DropdownOption(str(item.id), item.title) for item in projects]],
    )
    lifecycle = ft.Dropdown(
        label="Lifecycle",
        value="all",
        options=[ft.DropdownOption("all", "All lifecycle states"), *[
            ft.DropdownOption(value.value, value.value.replace("_", " ").title()) for value in TaskLifecycle
        ]],
    )
    filter_date = ft.TextField(label="Date (YYYY-MM-DD)")
    filter_week = ft.TextField(label="Week start (YYYY-MM-DD)")
    filter_importance = ft.Dropdown(
        label="Importance", value="any",
        options=[ft.DropdownOption("any", "Any"), ft.DropdownOption("yes", "Important"), ft.DropdownOption("no", "Not important")],
    )
    filter_urgency = ft.Dropdown(
        label="Urgency", value="any",
        options=[ft.DropdownOption("any", "Any"), ft.DropdownOption("yes", "Urgent"), ft.DropdownOption("no", "Not urgent")],
    )
    attention_only = ft.Switch(label="Needs Attention only")
    list_column = ft.Column(spacing=tokens.space_3)

    def render_list(_event=None, *, update=False):
        filters: dict[str, object] = {"search": search.value or ""}
        if filter_project.value != "all":
            filters["project_id"] = int(filter_project.value)
        if lifecycle.value != "all":
            filters["lifecycle"] = TaskLifecycle(lifecycle.value)
        if (filter_date.value or "").strip():
            filters["planned_date"] = _date_value(filter_date.value)
        if (filter_week.value or "").strip():
            filters["planned_week_start"] = _date_value(filter_week.value)
        if filter_importance.value != "any":
            filters["importance"] = filter_importance.value == "yes"
        if filter_urgency.value != "any":
            filters["urgency"] = filter_urgency.value == "yes"
        if attention_only.value:
            filters["attention_only"] = True
        task_controls: list[ft.Control] = []
        for item in services.tasks.list_tasks.execute(**filters):
            def edit(_event, task_id=item.task.id):
                state.selected_task_id = task_id
                refresh()
            def complete(_event, task_id=item.task.id):
                try:
                    services.tasks.complete_task.execute(task_id)
                    refresh()
                except Exception as error:
                    report_error(str(error))
            task_controls.append(task_row(item, tokens, on_complete=complete, on_edit=edit))
        list_column.controls = task_controls or [empty_state("No Tasks match these filters.", tokens)]
        if update:
            list_column.update()

    def apply_filters(_event):
        try:
            render_list(update=True)
        except Exception as error:
            report_error(str(error))

    render_list()
    controls: list[ft.Control] = [
        page_heading("Tasks", "Plan once, move transparently, and keep lifecycle separate from blockers.", tokens),
    ]
    if state.selected_task_id is not None:
        try:
            controls.append(build_task_editor_content(
                services, state.selected_task_id, tokens, refresh,
                lambda _e: _close_editor(state, refresh), report_error,
            ))
        except Exception as error:
            state.selected_task_id = None
            report_error(str(error))
    controls.extend([
        card("Create Task", [
            ft.Text("Choose an existing Project. Project creation remains a separate workflow.", color=tokens.text_muted, size=tokens.text_small),
            ft.ResponsiveRow([ft.Container(project, col={"sm": 12, "md": 4}), ft.Container(title, col={"sm": 12, "md": 8})]),
            ft.ResponsiveRow([ft.Container(planned_date, col={"sm": 12, "md": 4}), ft.Container(group, col={"sm": 12, "md": 4}), ft.Container(position, col={"sm": 12, "md": 4})]),
            definition, next_action, ft.Row([importance, urgency]), create_message,
            ft.Button("Create Task", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=create, disabled=not projects),
        ], tokens),
        card("Global Tasks", [
            ft.ResponsiveRow([
                ft.Container(search, col={"sm": 12, "lg": 6}),
                ft.Container(filter_project, col={"sm": 12, "md": 6, "lg": 3}),
                ft.Container(lifecycle, col={"sm": 12, "md": 6, "lg": 3}),
                ft.Container(filter_date, col={"sm": 12, "md": 6, "lg": 3}),
                ft.Container(filter_week, col={"sm": 12, "md": 6, "lg": 3}),
                ft.Container(filter_importance, col={"sm": 12, "md": 6, "lg": 3}),
                ft.Container(filter_urgency, col={"sm": 12, "md": 6, "lg": 3}),
            ], spacing=tokens.space_3, run_spacing=tokens.space_3),
            ft.Row([attention_only, ft.Button("Apply filters", on_click=apply_filters)]),
            list_column,
        ], tokens),
    ])
    return ft.Column(controls, spacing=tokens.space_5, scroll=ft.ScrollMode.AUTO, expand=True)


def _close_editor(state: AppSessionState, refresh):
    state.selected_task_id = None
    refresh()

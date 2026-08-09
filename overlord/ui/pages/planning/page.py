from __future__ import annotations

from datetime import date

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.planning.application import DailyPlanningReadModel, PlanningCandidate
from overlord.modules.planning.domain import TodayGroup
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.components.feedback import empty_state
from overlord.ui.components.layout import card, page_heading
from overlord.ui.components.status import state_chip
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError("Plan date must use YYYY-MM-DD.") from error


def _status_label(candidate: PlanningCandidate) -> str:
    lifecycle = candidate.item.task.lifecycle_status
    return lifecycle.value.replace("_", " ").title() if lifecycle else "Review status"


def build_daily_planning(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    report_error,
) -> ft.Control:
    parsed_query = route.partition("?")[2]
    query_values = dict(
        part.split("=", 1) for part in parsed_query.split("&") if "=" in part
    )
    try:
        selected_day = _date_value(query_values.get("date", date.today().isoformat()))
    except ValueError:
        selected_day = date.today()

    model: DailyPlanningReadModel = services.daily_planning.get_plan.execute(selected_day)
    primary_ids = [item.task.id for item in model.primary]
    secondary_ids = [item.task.id for item in model.secondary]
    item_by_id = {candidate.item.task.id: candidate.item for candidate in model.candidates}

    date_field = ft.TextField(label=ui_text("planning.date"), value=selected_day.isoformat(), width=180)
    search = ft.TextField(label=ui_text("planning.search"), expand=True)
    source = ft.Dropdown(
        label=ui_text("planning.source"),
        value="all",
        options=[
            ft.DropdownOption("all", ui_text("planning.all_sources")),
            ft.DropdownOption("current_week", ui_text("planning.current_week")),
            ft.DropdownOption("overdue", ui_text("planning.overdue")),
            ft.DropdownOption("active_cycle", ui_text("planning.active_cycle")),
        ],
        width=180,
    )
    project = ft.Dropdown(
        label=ui_text("planning.project"),
        value="all",
        options=[
            ft.DropdownOption("all", "All Projects"),
            *[ft.DropdownOption(str(item.id), item.title) for item in model.projects],
        ],
        width=200,
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)
    candidate_list = ft.Column(spacing=tokens.space_2)
    primary_list = ft.Column(spacing=tokens.space_2)
    secondary_list = ft.Column(spacing=tokens.space_2)
    primary_heading = ft.Text("", color=tokens.text_primary, weight=ft.FontWeight.W_600)
    secondary_heading = ft.Text("", color=tokens.text_primary, weight=ft.FontWeight.W_600)

    def show_message(value: str) -> None:
        message.value = value
        message.update()

    def assign(task_id: int, group: TodayGroup):
        def action(_event):
            target = primary_ids if group is TodayGroup.PRIMARY else secondary_ids
            capacity = 3 if group is TodayGroup.PRIMARY else 4
            if task_id in target:
                return
            if len(target) >= capacity:
                show_message(f"{group.value.title()} capacity is already full.")
                return
            if group is TodayGroup.PRIMARY and not item_by_id[task_id].task.definition_of_done:
                show_message("Definition of Done is required before assigning a Primary Task.")
                return
            if task_id in primary_ids:
                primary_ids.remove(task_id)
            if task_id in secondary_ids:
                secondary_ids.remove(task_id)
            target.append(task_id)
            message.value = ""
            render_all()
        return action

    def remove(task_id: int):
        def action(_event):
            if task_id in primary_ids:
                primary_ids.remove(task_id)
            if task_id in secondary_ids:
                secondary_ids.remove(task_id)
            message.value = ""
            render_all()
        return action

    def move(task_id: int, offset: int, group_ids: list[int]):
        def action(_event):
            index = group_ids.index(task_id)
            destination = index + offset
            if 0 <= destination < len(group_ids):
                group_ids[index], group_ids[destination] = group_ids[destination], group_ids[index]
                render_all()
        return action

    def candidate_control(candidate: PlanningCandidate) -> ft.Control:
        item = candidate.item
        task = item.task
        flags: list[str] = []
        if candidate.is_overdue:
            flags.append("Overdue")
        if candidate.in_active_cycle:
            flags.append("Active Cycle")
        if item.open_blockers:
            flags.append("Blocked")
        if item.current_plan:
            flags.append(item.current_plan.planned_date.strftime("%b %d"))
        metadata = " · ".join([item.project_title or ui_text("tasks.no_project"), *flags])
        status_colors = tokens.success if task.lifecycle_status is TaskLifecycle.COMPLETED else (
            tokens.info if task.lifecycle_status is TaskLifecycle.IN_PROGRESS else tokens.neutral
        )
        return ft.Container(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(task.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                            ft.Text(metadata, color=tokens.text_muted, size=tokens.text_small),
                        ],
                        spacing=tokens.space_1,
                        expand=True,
                    ),
                    state_chip(_status_label(candidate), status_colors, tokens),
                    ft.Column(
                        [
                            ft.TextButton(
                                ui_text("planning.assign_primary"),
                                on_click=assign(task.id, TodayGroup.PRIMARY),
                                disabled=task.id in primary_ids or (len(primary_ids) >= 3 and task.id not in primary_ids),
                            ),
                            ft.TextButton(
                                ui_text("planning.assign_secondary"),
                                on_click=assign(task.id, TodayGroup.SECONDARY),
                                disabled=task.id in secondary_ids or (len(secondary_ids) >= 4 and task.id not in secondary_ids),
                            ),
                        ],
                        spacing=tokens.space_0,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.space_2,
            ),
            bgcolor=tokens.surface_inner,
            border=ft.Border.all(tokens.border_width, tokens.border_default),
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
        )

    def plan_control(task_id: int, group_ids: list[int]) -> ft.Control:
        item = item_by_id[task_id]
        index = group_ids.index(task_id)
        return ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(str(index + 1), color=tokens.accent_primary, weight=ft.FontWeight.W_700),
                            ft.Column(
                                [
                                    ft.Text(item.task.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                                    ft.Text(item.project_title or ui_text("tasks.no_project"), color=tokens.text_muted, size=tokens.text_small),
                                ],
                                spacing=tokens.space_1,
                                expand=True,
                            ),
                        ],
                        spacing=tokens.space_2,
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                ui_text("planning.move_up"),
                                on_click=move(task_id, -1, group_ids),
                                disabled=index == 0,
                            ),
                            ft.TextButton(
                                ui_text("planning.move_down"),
                                on_click=move(task_id, 1, group_ids),
                                disabled=index == len(group_ids) - 1,
                            ),
                            ft.TextButton(ui_text("planning.remove"), on_click=remove(task_id)),
                        ],
                        wrap=True,
                        spacing=tokens.space_1,
                    ),
                ],
                spacing=tokens.space_1,
            ),
            bgcolor=tokens.surface_inner,
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
        )

    def filtered_candidates() -> list[PlanningCandidate]:
        search_value = (search.value or "").strip().lower()
        source_value = source.value or "all"
        project_value = project.value or "all"
        result = []
        for candidate in model.candidates:
            item = candidate.item
            project_title = item.project_title or ui_text("tasks.no_project")
            if search_value and search_value not in item.task.title.lower() and search_value not in project_title.lower():
                continue
            if project_value != "all" and item.task.project_id != int(project_value):
                continue
            if source_value == "current_week" and not candidate.in_current_week:
                continue
            if source_value == "overdue" and not candidate.is_overdue:
                continue
            if source_value == "active_cycle" and not candidate.in_active_cycle:
                continue
            result.append(candidate)
        return result

    def render_all(_event=None, *, update_controls: bool = True) -> None:
        matches = filtered_candidates()
        candidate_list.controls = [candidate_control(candidate) for candidate in matches] or [
            empty_state(ui_text("planning.no_candidates"), tokens)
        ]
        primary_heading.value = ui_text("planning.primary", count=len(primary_ids))
        secondary_heading.value = ui_text("planning.secondary", count=len(secondary_ids))
        primary_list.controls = [plan_control(task_id, primary_ids) for task_id in primary_ids] or [
            empty_state(ui_text("planning.empty_group"), tokens)
        ]
        secondary_list.controls = [plan_control(task_id, secondary_ids) for task_id in secondary_ids] or [
            empty_state(ui_text("planning.empty_group"), tokens)
        ]
        if update_controls:
            for control in (candidate_list, primary_heading, secondary_heading, primary_list, secondary_list, message):
                control.update()

    def load_date(_event) -> None:
        nonlocal model, item_by_id
        try:
            chosen = _date_value(date_field.value or "")
            model = services.daily_planning.get_plan.execute(chosen)
            primary_ids[:] = [item.task.id for item in model.primary]
            secondary_ids[:] = [item.task.id for item in model.secondary]
            item_by_id = {candidate.item.task.id: candidate.item for candidate in model.candidates}
            project.options = [
                ft.DropdownOption("all", "All Projects"),
                *[ft.DropdownOption(str(item.id), item.title) for item in model.projects],
            ]
            project.value = "all"
            message.value = ""
            render_all()
            project.update()
        except Exception as error:
            show_message(str(error))

    def save(_event) -> None:
        try:
            services.daily_planning.save_plan.execute(model.day, tuple(primary_ids), tuple(secondary_ids))
            navigate(f"/dashboard?date={model.day.isoformat()}")
        except Exception as error:
            show_message(str(error))

    search.on_change = render_all
    source.on_select = render_all
    project.on_select = render_all
    render_all(update_controls=False)

    return ft.Column(
        [
            page_heading(
                ui_text("planning.title"),
                ui_text("planning.subtitle"),
                tokens,
                [
                    ft.TextButton(ui_text("planning.cancel"), on_click=lambda _e: navigate("/dashboard")),
                    ft.Button(ui_text("planning.save"), bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=save),
                ],
            ),
            ft.Row([date_field, ft.Button(ui_text("planning.load_date"), on_click=load_date)], wrap=True),
            message,
            ft.ResponsiveRow(
                [
                    card(
                        ui_text("planning.find_tasks"),
                        [
                            ft.ResponsiveRow(
                                [
                                    ft.Container(search, col={"sm": 12, "lg": 5}),
                                    ft.Container(source, col={"sm": 6, "lg": 3}),
                                    ft.Container(project, col={"sm": 6, "lg": 4}),
                                ],
                                spacing=tokens.space_2,
                                run_spacing=tokens.space_2,
                            ),
                            candidate_list,
                        ],
                        tokens,
                        col={"sm": 12, "lg": 7},
                    ),
                    card(
                        "Today’s Plan",
                        [
                            primary_heading,
                            primary_list,
                            ft.Divider(color=tokens.border_default),
                            secondary_heading,
                            secondary_list,
                        ],
                        tokens,
                        col={"sm": 12, "lg": 5},
                    ),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
        ],
        spacing=tokens.space_4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

from __future__ import annotations

from datetime import date

import flet as ft

from overlord.application import ApplicationServices
from overlord.domain.cycles import CycleStatus, WeeklyOutcomeStatus
from overlord.presentation.components.common import card, empty_state, page_heading, state_chip, task_row
from overlord.presentation.design_system.tokens import ThemeTokens


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError("Start date must use YYYY-MM-DD.") from error


def build_cycles(services, tokens, route, navigate, refresh, report_error):
    if route.startswith("/cycles/"):
        return _build_detail(services, tokens, route, navigate, refresh, report_error)
    title = ft.TextField(label="Cycle title")
    outcome = ft.TextField(label="Main outcome", multiline=True, min_lines=2, max_lines=4)
    start = ft.TextField(label="Start date", value=date.today().isoformat())
    default_length = services.settings.get_settings.execute().default_cycle_length
    length = ft.TextField(label="Length in weeks", value=str(default_length), keyboard_type=ft.KeyboardType.NUMBER)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def create(_event):
        try:
            cycle = services.cycles.create_cycle.execute(title.value or "", outcome.value or "", _parse_date(start.value or ""), int(length.value or default_length))
            navigate(f"/cycles/{cycle.id}")
        except Exception as error:
            message.value = str(error)
            message.update()

    cycles = services.cycles.search_cycles.execute()
    list_column = ft.Column(spacing=tokens.space_3)

    def render_list(search: str = "", status: str = "all"):
        filtered = [cycle for cycle in cycles if search.lower() in cycle.title.lower() or search.lower() in cycle.main_outcome.lower()]
        if status != "all":
            filtered = [cycle for cycle in filtered if cycle.status.value == status]
        colors = {CycleStatus.DRAFT: tokens.neutral, CycleStatus.ACTIVE: tokens.success, CycleStatus.COMPLETED: tokens.info, CycleStatus.ARCHIVED: tokens.neutral}
        list_column.controls = [
            ft.Container(
                ft.Row([
                    ft.Column([
                        ft.Text(cycle.title, color=tokens.text_primary, weight=ft.FontWeight.W_600, size=tokens.text_emphasis),
                        ft.Text(cycle.main_outcome, color=tokens.text_muted, size=tokens.text_small, max_lines=2),
                        ft.Text(f"{cycle.start_date.isoformat()} – {cycle.end_date.isoformat()}", color=tokens.text_muted, size=tokens.text_small),
                    ], expand=True, spacing=tokens.space_1),
                    state_chip(cycle.status.value.title(), colors[cycle.status], tokens),
                    ft.TextButton("Open", on_click=lambda _e, cycle_id=cycle.id: navigate(f"/cycles/{cycle_id}")),
                ]),
                bgcolor=tokens.surface_inner,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
            for cycle in filtered
        ] or [empty_state("No Cycles match these filters.", tokens)]

    search = ft.TextField(label="Search Cycles", expand=True)
    status = ft.Dropdown(
        label="State",
        value="all",
        options=[ft.DropdownOption("all", "All"), *[ft.DropdownOption(value.value, value.value.title()) for value in CycleStatus]],
    )

    def filter_list(_event):
        render_list(search.value or "", status.value or "all")
        list_column.update()

    search.on_change = filter_list
    status.on_select = filter_list
    render_list()
    return ft.Column([
        page_heading("12-Week Plans", "Turn a main outcome into a visible weekly structure.", tokens),
        card("Create Cycle", [title, outcome, ft.Row([start, length]), message, ft.Button("Create Cycle", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=create)], tokens),
        card("Cycles", [ft.Row([search, status]), list_column], tokens),
    ], spacing=tokens.space_5, scroll=ft.ScrollMode.AUTO, expand=True)


def _build_detail(services: ApplicationServices, tokens: ThemeTokens, route: str, navigate, refresh, report_error):
    try:
        cycle_id = int(route.rsplit("/", 1)[1])
        detail = services.cycles.get_detail.execute(cycle_id)
    except Exception as error:
        return ft.Column([page_heading("Cycle unavailable", str(error), tokens), ft.Button("Back to Cycles", on_click=lambda _e: navigate("/cycles"))])
    cycle = detail.cycle
    projects = services.projects.list_projects.execute()
    tasks = services.tasks.list_tasks.execute()
    project_selector = ft.Dropdown(label="Project", options=[ft.DropdownOption(str(project.id), project.title) for project in projects], value=str(projects[0].id) if projects else None)
    task_selector = ft.Dropdown(label="Task", options=[ft.DropdownOption(str(item.task.id), item.task.title) for item in tasks], value=str(tasks[0].task.id) if tasks else None)

    def change_status(status):
        def action(_event):
            try:
                services.cycles.change_status.execute(cycle.id, status)
                refresh()
            except Exception as error:
                report_error(str(error))
        return action

    def connect_project(_event):
        try:
            services.cycles.connect_project.execute(cycle.id, int(project_selector.value))
            refresh()
        except Exception as error:
            report_error(str(error))

    def connect_task(_event):
        try:
            services.cycles.connect_task.execute(cycle.id, int(task_selector.value))
            refresh()
        except Exception as error:
            report_error(str(error))

    milestone_title = ft.TextField(label="Milestone title", expand=True)
    milestone_dod = ft.TextField(label="Definition of Done", expand=True)

    def add_milestone(_event):
        try:
            services.cycles.connect_milestone.execute(cycle.id, int(project_selector.value), milestone_title.value or "", milestone_dod.value or "")
            refresh()
        except Exception as error:
            report_error(str(error))

    week = ft.Dropdown(label="Week", value="1", options=[ft.DropdownOption(str(number), f"Week {number}") for number in range(1, cycle.length_weeks + 1)])
    week_title = ft.TextField(label="Weekly outcome", expand=True)
    week_dod = ft.TextField(label="Definition of Done", expand=True)
    week_status = ft.Dropdown(
        label="Outcome state",
        value=WeeklyOutcomeStatus.PLANNED.value,
        options=[ft.DropdownOption(value.value, value.value.replace("_", " ").title()) for value in WeeklyOutcomeStatus],
    )

    def save_week(_event):
        try:
            services.cycles.set_weekly_outcome.execute(
                cycle.id, int(week.value), week_title.value or "", week_dod.value or "", WeeklyOutcomeStatus(week_status.value)
            )
            refresh()
        except Exception as error:
            report_error(str(error))

    outcomes_by_week = {item.week_number: item for item in detail.weekly_outcomes}
    week_controls = []
    for number in range(1, cycle.length_weeks + 1):
        item = outcomes_by_week.get(number)
        week_controls.append(
            ft.Container(
                ft.Column([
                    ft.Text(f"Week {number}", color=tokens.accent_primary, weight=ft.FontWeight.W_600),
                    ft.Text(item.title if item else "Outcome not set", color=tokens.text_primary if item else tokens.text_muted, max_lines=2),
                    ft.Text(item.status.value.replace("_", " ").title() if item else "Not set", color=tokens.text_muted, size=tokens.text_small),
                ], spacing=tokens.space_1),
                bgcolor=tokens.surface_inner,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
                col={"sm": 12, "md": 6, "lg": 4},
            )
        )
    return ft.Column([
        page_heading(cycle.title, cycle.main_outcome, tokens, [ft.TextButton("All Cycles", on_click=lambda _e: navigate("/cycles"))]),
        ft.ResponsiveRow([
            card("Cycle", [
                ft.Text(f"{cycle.start_date.isoformat()} – {cycle.end_date.isoformat()}", color=tokens.text_secondary),
                ft.Text(f"{cycle.length_weeks} weeks · {cycle.status.value.title()}", color=tokens.text_primary),
                ft.Row([
                    ft.TextButton("Draft", on_click=change_status(CycleStatus.DRAFT)),
                    ft.TextButton("Activate", on_click=change_status(CycleStatus.ACTIVE)),
                    ft.TextButton("Complete", on_click=change_status(CycleStatus.COMPLETED)),
                    ft.TextButton("Archive", on_click=change_status(CycleStatus.ARCHIVED)),
                ], wrap=True),
            ], tokens, col={"sm": 12, "lg": 5}),
            card("Connections", [
                ft.Row([project_selector, ft.Button("Connect Project", on_click=connect_project, disabled=not projects)]),
                ft.Row([task_selector, ft.Button("Connect Task", on_click=connect_task, disabled=not tasks)]),
                ft.Text("Projects remain independent and can join multiple Cycles over time.", color=tokens.text_muted, size=tokens.text_small),
            ], tokens, col={"sm": 12, "lg": 7}),
        ], spacing=tokens.space_4, run_spacing=tokens.space_4),
        card("Twelve-Week Structure", [ft.ResponsiveRow(week_controls, spacing=tokens.space_3, run_spacing=tokens.space_3)], tokens),
        ft.ResponsiveRow([
            card("Connected Projects", [
                *[ft.Text(project.title, color=tokens.text_primary) for project in detail.projects]
            ] or [empty_state("No connected Projects.", tokens)], tokens, col={"sm": 12, "lg": 6}),
            card("Milestones", [
                *[ft.Text(f"{milestone.title} · {milestone.status.value.replace('_', ' ').title()}", color=tokens.text_primary) for milestone in detail.milestones],
                ft.Row([milestone_title, milestone_dod]),
                ft.Button("Add Milestone", on_click=add_milestone, disabled=not projects),
            ], tokens, col={"sm": 12, "lg": 6}),
        ], spacing=tokens.space_4, run_spacing=tokens.space_4),
        card("Connected Tasks", [task_row(item, tokens) for item in detail.tasks] or [empty_state("No connected Tasks.", tokens)], tokens),
        card("Set Weekly Outcome", [ft.Row([week, week_status]), week_title, week_dod, ft.Button("Save Weekly Outcome", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=save_week)], tokens),
    ], spacing=tokens.space_5, scroll=ft.ScrollMode.AUTO, expand=True)

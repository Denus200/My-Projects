from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.cycles.read_models import CycleDetail, CycleSummary
from overlord.modules.cycles.application import WeeklyOutcomeDraft
from overlord.modules.cycles.domain import CycleStatus, WeeklyOutcomeStatus, cycle_end_date
from overlord.modules.projects.domain import ProjectStatus
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.components.controls import checkbox, primary_button, search_field, secondary_button, select_field, text_field
from overlord.ui.components.dialogs import close_dialog, dialog_footer
from overlord.ui.components.feedback import empty_state, show_success
from overlord.ui.components.layout import card, page_container
from overlord.ui.components.status import state_chip
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import StateColors, ThemeTokens
from overlord.ui.state import AppSessionState, CycleFilterState, CycleWizardState
from overlord.ui.strings import format_date_with_year, format_short_date, ui_error, ui_text


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(ui_text("cycles.date_error")) from error


def _status_label(status: CycleStatus) -> str:
    return ui_text(f"cycles.status.{status.value}")


def _cycle_status_color(status: CycleStatus, tokens: ThemeTokens) -> StateColors:
    return {
        CycleStatus.DRAFT: tokens.neutral,
        CycleStatus.ACTIVE: tokens.success,
        CycleStatus.COMPLETED: tokens.info,
        CycleStatus.ARCHIVED: tokens.neutral,
    }[status]


def _outcome_status_color(status: WeeklyOutcomeStatus, tokens: ThemeTokens) -> StateColors:
    return {
        WeeklyOutcomeStatus.PLANNED: tokens.neutral,
        WeeklyOutcomeStatus.ACHIEVED: tokens.success,
        WeeklyOutcomeStatus.PARTIAL: tokens.warning,
        WeeklyOutcomeStatus.NOT_ACHIEVED: tokens.blocker,
    }[status]


def _outcome_status_label(status: WeeklyOutcomeStatus) -> str:
    return ui_text(f"cycles.outcome_status.{status.value}")


def _date_range(start: date, end: date) -> str:
    return ui_text("common.date_range", start=format_date_with_year(start), end=format_date_with_year(end))


def _week_dates(start: date, week_number: int) -> tuple[date, date]:
    week_start = start + timedelta(weeks=week_number - 1)
    return week_start, week_start + timedelta(days=6)


def _week_context(cycle, as_of: date | None = None) -> int | None:
    selected = as_of or date.today()
    if cycle.status is not CycleStatus.ACTIVE:
        return None
    if not cycle.start_date <= selected <= cycle.end_date:
        return None
    return min(cycle.length_weeks, (selected - cycle.start_date).days // 7 + 1)


def _summary_progress(summary: CycleSummary, tokens: ThemeTokens) -> list[ft.Control]:
    denominator = summary.scheduled_outcome_count
    if not denominator:
        return [ft.Text(ui_text("cycles.progress_unavailable"), color=tokens.text_muted)]
    parts = [ui_text("cycles.progress_achieved", count=summary.achieved_count)]
    if summary.partial_count:
        parts.append(ui_text("cycles.progress_partial", count=summary.partial_count))
    if summary.planned_count:
        parts.append(ui_text("cycles.progress_remaining", count=summary.planned_count))
    if summary.not_achieved_count:
        parts.append(ui_text("cycles.progress_not_achieved", count=summary.not_achieved_count))
    if summary.unplanned_week_count:
        parts.append(ui_text("cycles.progress_unplanned", count=summary.unplanned_week_count))
    return [
        ft.Text(
            ui_text("cycles.progress_fraction", achieved=summary.achieved_count, planned=denominator),
            color=tokens.text_primary,
            weight=ft.FontWeight.W_600,
        ),
        ft.ProgressBar(
            value=summary.achieved_count / denominator,
            color=tokens.accent_primary,
            bgcolor=tokens.border_default,
            border_radius=tokens.radius_pill,
        ),
        ft.Text(" - ".join(parts), color=tokens.text_muted, size=tokens.text_small),
    ]


def _cycle_card(summary: CycleSummary, tokens: ThemeTokens, navigate) -> ft.Container:
    cycle = summary.cycle
    week = summary.current_week(date.today())
    projects = " - ".join(project.title for project in summary.projects) or ui_text("cycles.no_projects_compact")
    next_context = summary.next_milestone.title if summary.next_milestone else ui_text("cycles.no_milestone_compact")
    date_copy = _date_range(cycle.start_date, cycle.end_date)
    if week is not None:
        date_copy += " - " + ui_text("cycles.week_of", week=week, length=cycle.length_weeks)
    return ft.Container(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(cycle.title, color=tokens.text_primary, weight=ft.FontWeight.W_600, size=tokens.text_emphasis, expand=True),
                        state_chip(_status_label(cycle.status), _cycle_status_color(cycle.status, tokens), tokens),
                    ]
                ),
                ft.Text(date_copy, color=tokens.text_muted, size=tokens.text_small),
                ft.Column(
                    [
                        ft.Text(ui_text("cycles.main_outcome"), color=tokens.text_muted, size=tokens.text_small),
                        ft.Text(cycle.main_outcome, color=tokens.text_primary, max_lines=3),
                    ],
                    spacing=tokens.space_1,
                ),
                ft.Text(ui_text("cycles.weekly_progress"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
                *_summary_progress(summary, tokens),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Text(ui_text("cycles.connected_projects"), color=tokens.text_muted, size=tokens.text_small),
                                    ft.Text(projects, color=tokens.text_primary, max_lines=2),
                                ],
                                spacing=tokens.space_1,
                            ),
                            col={"sm": 12, "md": 7},
                        ),
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Text(ui_text("cycles.next_context"), color=tokens.text_muted, size=tokens.text_small),
                                    ft.Text(next_context, color=tokens.text_primary, max_lines=2),
                                ],
                                spacing=tokens.space_1,
                            ),
                            col={"sm": 12, "md": 5},
                        ),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_2,
                ),
                ft.Row(
                    [
                        ft.Container(expand=True),
                        ft.TextButton(ui_text("cycles.open"), on_click=lambda _e: navigate(f"/cycles/{cycle.id}")),
                    ]
                ),
            ],
            spacing=tokens.space_3,
        ),
        bgcolor=tokens.surface_inner,
        border=ft.Border.all(tokens.border_width, tokens.accent_primary if cycle.status is CycleStatus.ACTIVE else tokens.border_default),
        border_radius=tokens.radius_medium,
        padding=tokens.space_4,
    )


def build_cycles(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    refresh,
    report_error,
    state: AppSessionState | None = None,
    page: ft.Page | None = None,
) -> ft.Control:
    state = state or AppSessionState(route=route)
    if route == "/cycles/new":
        return _build_wizard(services, tokens, navigate, report_error, state, page)
    if route.startswith("/cycles/"):
        return _build_detail(services, tokens, route, navigate, refresh, report_error, page)
    return _build_list(services, tokens, navigate, report_error, state)


def _build_list(services, tokens, navigate, report_error, state):
    filter_state = state.cycle_filters or CycleFilterState()
    state.cycle_filters = filter_state
    search = search_field(tokens, label=ui_text("cycles.search"), value=filter_state.search, expand=True)
    status = select_field(
        tokens,
        label=ui_text("cycles.status_filter"),
        value=filter_state.status,
        options=[
            ft.DropdownOption("all", ui_text("cycles.status_all")),
            *[ft.DropdownOption(value.value, _status_label(value)) for value in CycleStatus],
        ],
    )
    count = ft.Text("", color=tokens.text_muted, size=tokens.text_small)
    results = ft.Column(spacing=tokens.space_3)

    def remember() -> None:
        filter_state.search = search.value or ""
        filter_state.status = status.value or "all"

    def clear_filters(_event) -> None:
        search.value = ""
        status.value = "all"
        search.update()
        status.update()
        render(update=True)

    def render(_event=None, *, update: bool = False) -> None:
        remember()
        selected = None if filter_state.status == "all" else CycleStatus(filter_state.status)
        summaries = services.cycles.list_summaries.execute(selected, filter_state.search)
        if summaries:
            results.controls = [_cycle_card(item, tokens, navigate) for item in summaries]
        elif filter_state.search or filter_state.status != "all":
            results.controls = [
                empty_state(
                    ui_text("cycles.empty_filtered"),
                    tokens,
                    ft.TextButton(ui_text("cycles.clear_filters"), on_click=clear_filters),
                )
            ]
        else:
            results.controls = [
                empty_state(
                    ui_text("cycles.empty_all"),
                    tokens,
                    primary_button(ui_text("cycles.create_action"), tokens, on_click=lambda _e: navigate("/cycles/new")),
                )
            ]
        count.value = ui_text("cycles.results_count", count=len(summaries))
        if update:
            results.update()
            count.update()

    def apply(_event) -> None:
        try:
            render(update=True)
        except Exception as error:
            report_error(ui_error(error))

    search.on_submit = apply
    status.on_select = apply
    render()
    return page_container(
        ui_text("cycles.title"),
        [
            card(
                ui_text("cycles.browse"),
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(search, col={"sm": 12, "md": 7}),
                            ft.Container(status, col={"sm": 12, "md": 3}),
                            ft.Container(ft.TextButton(ui_text("cycles.clear_filters"), on_click=clear_filters), col={"sm": 12, "md": 2}),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_2,
                    ),
                    count,
                    results,
                ],
                tokens,
            ),
        ],
        tokens,
        subtitle=ui_text("cycles.subtitle"),
        actions=[
            primary_button(
                ft.Row(
                    [
                        lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("cycles.create_action")),
                        ft.Text(ui_text("cycles.create_action"), color=tokens.on_accent),
                    ],
                    spacing=tokens.space_2,
                    tight=True,
                ),
                tokens,
                on_click=lambda _e: navigate("/cycles/new"),
            )
        ],
        content_spacing=tokens.space_5,
        page_id="cycles",
    )


def _build_wizard(services, tokens, navigate, report_error, state, page):
    settings = services.settings.get_settings.execute()
    wizard = state.cycle_wizard or CycleWizardState(
        start_date=date.today().isoformat(),
        length_weeks=settings.default_cycle_length,
    )
    state.cycle_wizard = wizard
    options = services.cycles.get_wizard_options.execute()
    host = ft.Container(expand=True)
    error_text = ft.Text("", color=tokens.error.text, size=tokens.text_small)
    step_names = (
        ui_text("cycles.step.identity"),
        ui_text("cycles.step.dates"),
        ui_text("cycles.step.connections"),
        ui_text("cycles.step.weekly"),
        ui_text("cycles.step.review"),
    )
    save_current: Callable[[], None] = lambda: None

    def indicator() -> ft.ResponsiveRow:
        return ft.ResponsiveRow(
            [
                ft.Container(
                    ft.Text(
                        ui_text("cycles.step_label", number=number, name=name),
                        color=tokens.on_accent if number == wizard.step else tokens.text_secondary,
                        size=tokens.text_small,
                        weight=ft.FontWeight.W_600 if number == wizard.step else ft.FontWeight.W_400,
                    ),
                    bgcolor=tokens.accent_primary if number == wizard.step else tokens.surface_inner,
                    border=ft.Border.all(tokens.border_width, tokens.accent_primary if number <= wizard.step else tokens.border_default),
                    border_radius=tokens.radius_pill,
                    padding=ft.Padding.symmetric(horizontal=tokens.space_3, vertical=tokens.space_2),
                    col={"sm": 12, "md": 6, "lg": 2},
                )
                for number, name in enumerate(step_names, start=1)
            ],
            spacing=tokens.space_2,
            run_spacing=tokens.space_2,
        )

    def cancel(_event) -> None:
        state.cycle_wizard = None
        navigate("/cycles")

    def render_step(*, update: bool = False) -> None:
        nonlocal save_current
        error_text.value = ""
        if wizard.step == 1:
            title = text_field(tokens, label=ui_text("cycles.field_title"), value=wizard.title, autofocus=True)
            outcome = text_field(
                tokens,
                label=ui_text("cycles.field_main_outcome"),
                value=wizard.main_outcome,
                multiline=True,
                min_lines=3,
                max_lines=5,
            )

            def save_identity() -> None:
                wizard.title = title.value or ""
                wizard.main_outcome = outcome.value or ""
                title.error = None
                outcome.error = None
                if not wizard.title.strip():
                    title.error = ui_text("cycles.title_required")
                    title.update()
                    raise ValueError(title.error)
                if not wizard.main_outcome.strip():
                    outcome.error = ui_text("cycles.outcome_required")
                    outcome.update()
                    raise ValueError(outcome.error)

            save_current = save_identity
            body = [
                title,
                outcome,
                ft.Text(ui_text("cycles.main_outcome_help"), color=tokens.text_muted, size=tokens.text_small),
            ]
        elif wizard.step == 2:
            start = text_field(tokens, label=ui_text("cycles.field_start"), value=wizard.start_date)
            length = text_field(tokens, label=ui_text("cycles.field_length"), value=str(wizard.length_weeks), keyboard_type=ft.KeyboardType.NUMBER)
            ends = ft.Text("", color=tokens.text_primary, weight=ft.FontWeight.W_600)

            def calculate() -> tuple[date, int]:
                selected_start = _parse_date(start.value or "")
                try:
                    selected_length = int(length.value or "")
                except ValueError as error:
                    raise ValueError(ui_text("cycles.length_error")) from error
                selected_end = cycle_end_date(selected_start, selected_length)
                ends.value = ui_text("cycles.ends_value", date=format_date_with_year(selected_end))
                return selected_start, selected_length

            try:
                calculate()
            except ValueError:
                ends.value = ui_text("cycles.ends_pending")

            def update_end(_event) -> None:
                try:
                    calculate()
                except ValueError:
                    ends.value = ui_text("cycles.ends_pending")
                ends.update()

            start.on_change = update_end
            length.on_change = update_end

            def save_dates() -> None:
                start.error = None
                length.error = None
                try:
                    selected_start, selected_length = calculate()
                    wizard.start_date = selected_start.isoformat()
                    wizard.length_weeks = selected_length
                except ValueError as error:
                    text = ui_error(error)
                    if "date" in text.lower():
                        start.error = text
                        start.update()
                    else:
                        length.error = text
                        length.update()
                    raise

            save_current = save_dates
            body = [
                ft.ResponsiveRow(
                    [
                        ft.Container(start, col={"sm": 12, "md": 7}),
                        ft.Container(length, col={"sm": 12, "md": 5}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_2,
                ),
                ends,
            ]
        elif wizard.step == 3:
            project_checks = {
                item.project.id: checkbox(
                    tokens,
                    label=f"{item.project.title} - {item.project.stage_label or ui_text('cycles.stage_not_set')} - {_project_status_label(item.project.status)}",
                    value=item.project.id in wizard.selected_project_ids,
                )
                for item in options.projects
            }
            project_titles = {item.project.id: item.project.title for item in options.projects}
            milestone_checks = {
                item.id: checkbox(
                    tokens,
                    label=f"{project_titles.get(item.project_id, ui_text('cycles.unknown_project'))} - {item.title}",
                    value=item.id in wizard.selected_milestone_ids,
                )
                for item in options.milestones
            }

            def save_connections() -> None:
                selected_projects = {project_id for project_id, control in project_checks.items() if control.value}
                selected_milestones = {milestone_id for milestone_id, control in milestone_checks.items() if control.value}
                milestones = {item.id: item for item in options.milestones}
                for milestone_id in selected_milestones:
                    selected_projects.add(milestones[milestone_id].project_id)
                wizard.selected_project_ids = selected_projects
                wizard.selected_milestone_ids = selected_milestones

            save_current = save_connections
            body = [
                ft.Text(ui_text("cycles.connections_help"), color=tokens.text_secondary),
                ft.Text(ui_text("cycles.projects_section"), color=tokens.text_primary, weight=ft.FontWeight.W_600),
                ft.Column(list(project_checks.values()), spacing=tokens.space_1)
                if project_checks
                else empty_state(ui_text("cycles.projects_unavailable"), tokens),
                ft.Text(ui_text("cycles.milestones_section"), color=tokens.text_primary, weight=ft.FontWeight.W_600),
                ft.Column(list(milestone_checks.values()), spacing=tokens.space_1)
                if milestone_checks
                else ft.Text(ui_text("cycles.milestones_unavailable"), color=tokens.text_muted),
            ]
        elif wizard.step == 4:
            title_fields: dict[int, ft.TextField] = {}
            definition_fields: dict[int, ft.TextField] = {}
            week_rows: list[ft.Control] = []
            start_value = _parse_date(wizard.start_date)
            for number in range(1, wizard.length_weeks + 1):
                week_start, week_end = _week_dates(start_value, number)
                title_field = text_field(
                    tokens,
                    label=ui_text("cycles.week_outcome"),
                    value=wizard.weekly_titles.get(number, ""),
                    dense=True,
                )
                definition_field = text_field(
                    tokens,
                    label=ui_text("cycles.week_definition"),
                    value=wizard.weekly_definitions.get(number, ""),
                    dense=True,
                )
                title_fields[number] = title_field
                definition_fields[number] = definition_field
                week_rows.append(
                    ft.Container(
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    ft.Column(
                                        [
                                            ft.Text(ui_text("cycles.week_number", number=number), color=tokens.text_primary, weight=ft.FontWeight.W_600),
                                            ft.Text(ui_text("common.date_range", start=format_short_date(week_start), end=format_short_date(week_end)), color=tokens.text_muted, size=tokens.text_small),
                                        ],
                                        spacing=tokens.space_1,
                                    ),
                                    col={"sm": 12, "md": 2},
                                ),
                                ft.Container(title_field, col={"sm": 12, "md": 5}),
                                ft.Container(definition_field, col={"sm": 12, "md": 5}),
                            ],
                            spacing=tokens.space_2,
                            run_spacing=tokens.space_2,
                        ),
                        border=ft.Border(bottom=ft.BorderSide(tokens.border_width, tokens.border_default)),
                        padding=ft.Padding.symmetric(vertical=tokens.space_2),
                    )
                )

            def save_weeks() -> None:
                wizard.weekly_titles = {number: (field.value or "") for number, field in title_fields.items()}
                wizard.weekly_definitions = {number: (field.value or "") for number, field in definition_fields.items()}
                for number, title_field in title_fields.items():
                    title_field.error = None
                    definition_fields[number].error = None
                    if (title_field.value or "").strip() and not (definition_fields[number].value or "").strip():
                        definition_fields[number].error = ui_text("cycles.week_definition_required")
                        definition_fields[number].update()
                        raise ValueError(ui_text("cycles.week_error", number=number))
                    if not (title_field.value or "").strip() and (definition_fields[number].value or "").strip():
                        title_field.error = ui_text("cycles.week_title_required")
                        title_field.update()
                        raise ValueError(ui_text("cycles.week_error", number=number))

            save_current = save_weeks
            body = [
                ft.Text(ui_text("cycles.weekly_help"), color=tokens.text_secondary),
                ft.Column(week_rows, spacing=0),
            ]
        else:
            selected_projects = [item.project for item in options.projects if item.project.id in wizard.selected_project_ids]
            selected_milestones = [item for item in options.milestones if item.id in wizard.selected_milestone_ids]
            populated_weeks = [
                (number, title)
                for number, title in sorted(wizard.weekly_titles.items())
                if title.strip()
            ]
            start_value = _parse_date(wizard.start_date)
            end_value = cycle_end_date(start_value, wizard.length_weeks)
            save_current = lambda: None
            body = [
                ft.Text(wizard.title.strip(), color=tokens.text_primary, size=tokens.text_title, weight=ft.FontWeight.W_600),
                ft.Text(wizard.main_outcome.strip(), color=tokens.text_secondary),
                ft.Text(_date_range(start_value, end_value), color=tokens.text_primary),
                ft.Text(ui_text("cycles.length_value", count=wizard.length_weeks), color=tokens.text_muted),
                ft.Text(ui_text("cycles.review_projects", value=" - ".join(item.title for item in selected_projects) or ui_text("cycles.none")), color=tokens.text_secondary),
                ft.Text(ui_text("cycles.review_milestones", value=" - ".join(item.title for item in selected_milestones) or ui_text("cycles.none")), color=tokens.text_secondary),
                ft.Text(ui_text("cycles.review_weekly", count=len(populated_weeks), length=wizard.length_weeks), color=tokens.text_secondary),
                *[
                    ft.Text(ui_text("cycles.review_week", number=number, title=title.strip()), color=tokens.text_muted, size=tokens.text_small)
                    for number, title in populated_weeks
                ],
                (
                    ft.Container(
                        ft.Text(
                            ui_text("cycles.active_conflict", title=options.active_cycle.title),
                            color=tokens.warning.text,
                        ),
                        bgcolor=tokens.warning.background,
                        border_radius=tokens.radius_medium,
                        padding=tokens.space_3,
                    )
                    if options.active_cycle
                    else ft.Container()
                ),
            ]

        def back(_event) -> None:
            try:
                save_current()
            except ValueError:
                pass
            wizard.step = max(1, wizard.step - 1)
            render_step(update=True)

        def next_step(_event) -> None:
            try:
                save_current()
                wizard.step = min(5, wizard.step + 1)
                render_step(update=True)
            except Exception as error:
                error_text.value = ui_error(error)
                error_text.update()

        def create(activate: bool):
            def action(_event) -> None:
                try:
                    weekly = tuple(
                        WeeklyOutcomeDraft(number, title.strip(), wizard.weekly_definitions.get(number, "").strip())
                        for number, title in sorted(wizard.weekly_titles.items())
                        if title.strip()
                    )
                    cycle = services.cycles.create_plan.execute(
                        wizard.title,
                        wizard.main_outcome,
                        _parse_date(wizard.start_date),
                        wizard.length_weeks,
                        project_ids=tuple(sorted(wizard.selected_project_ids)),
                        milestone_ids=tuple(sorted(wizard.selected_milestone_ids)),
                        weekly_outcomes=weekly,
                        activate=activate,
                    )
                    state.cycle_wizard = None
                    show_success(page, tokens, ui_text("cycles.created_active" if activate else "cycles.created_draft"))
                    navigate(f"/cycles/{cycle.id}")
                except Exception as error:
                    error_text.value = ui_error(error)
                    error_text.update()

            return action

        actions: list[ft.Control] = [ft.TextButton(ui_text("cycles.cancel"), on_click=cancel)]
        if wizard.step > 1:
            actions.append(ft.TextButton(ui_text("cycles.back"), on_click=back))
        if wizard.step < 5:
            actions.append(primary_button(ui_text("cycles.continue"), tokens, on_click=next_step))
        else:
            actions.extend(
                [
                    ft.TextButton(ui_text("cycles.create_draft"), on_click=create(False)),
                    primary_button(
                        ui_text("cycles.create_activate"),
                        tokens,
                        on_click=create(True),
                        disabled=options.active_cycle is not None,
                    ),
                ]
            )
        host.content = ft.Column(
            [
                indicator(),
                card(step_names[wizard.step - 1], body, tokens),
                error_text,
                ft.Row(actions, alignment=ft.MainAxisAlignment.END, wrap=True),
            ],
            spacing=tokens.space_4,
        )
        if update:
            host.update()

    render_step()
    return page_container(
        ui_text("cycles.create_title"),
        [
            host,
        ],
        tokens,
        subtitle=ui_text("cycles.create_subtitle"),
        content_spacing=tokens.space_5,
        page_id="cycles",
    )


def _project_status_label(status: ProjectStatus) -> str:
    return ui_text(f"projects.status.{status.value}")


def _build_detail(services, tokens, route, navigate, refresh, report_error, page):
    try:
        cycle_id = int(route.rsplit("/", 1)[1])
        detail = services.cycles.get_detail.execute(cycle_id)
    except Exception as error:
        return page_container(
            ui_text("cycles.unavailable"),
            [
                secondary_button(ui_text("cycles.all_cycles"), tokens, on_click=lambda _e: navigate("/cycles")),
            ],
            tokens,
            subtitle=ui_error(error),
            page_id="cycles",
        )
    cycle = detail.cycle
    outcomes = {item.week_number: item for item in detail.weekly_outcomes}
    achieved = sum(item.status is WeeklyOutcomeStatus.ACHIEVED for item in detail.weekly_outcomes)
    partial = sum(item.status is WeeklyOutcomeStatus.PARTIAL for item in detail.weekly_outcomes)
    not_achieved = sum(item.status is WeeklyOutcomeStatus.NOT_ACHIEVED for item in detail.weekly_outcomes)
    planned = sum(item.status is WeeklyOutcomeStatus.PLANNED for item in detail.weekly_outcomes)
    denominator = len(detail.weekly_outcomes)
    current_week = _week_context(cycle)

    def edit_week(number: int):
        def open_editor(_event) -> None:
            if page is None or cycle.status is CycleStatus.ARCHIVED:
                return
            item = outcomes.get(number)
            title = text_field(tokens, label=ui_text("cycles.week_outcome"), value=item.title if item else "", autofocus=True)
            definition = text_field(
                tokens,
                label=ui_text("cycles.week_definition"),
                value=item.definition_of_done if item else "",
                multiline=True,
                min_lines=2,
                max_lines=4,
            )
            status = select_field(
                tokens,
                label=ui_text("cycles.outcome_status"),
                value=item.status.value if item else WeeklyOutcomeStatus.PLANNED.value,
                options=[ft.DropdownOption(value.value, _outcome_status_label(value)) for value in WeeklyOutcomeStatus],
            )
            message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

            def save(_save_event) -> None:
                try:
                    services.cycles.set_weekly_outcome.execute(
                        cycle.id,
                        number,
                        title.value or "",
                        definition.value or "",
                        WeeklyOutcomeStatus(status.value),
                    )
                    close_dialog(page)
                    show_success(page, tokens, ui_text("cycles.week_updated"))
                    refresh()
                except Exception as error:
                    message.value = ui_error(error)
                    message.update()

            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ui_text("cycles.edit_week", number=number),
                    content=ft.Container(ft.Column([title, definition, status, message], spacing=tokens.space_3, tight=True), width=560),
                    actions=dialog_footer(
                        ui_text("cycles.cancel"),
                        ui_text("cycles.save_week"),
                        lambda _e: close_dialog(page),
                        save,
                        tokens,
                    ),
                    bgcolor=tokens.surface_elevated,
                    scrollable=True,
                )
            )

        return open_editor

    def open_lifecycle(_event) -> None:
        if page is None:
            return
        selected = select_field(
            tokens,
            label=ui_text("cycles.status_filter"),
            value=cycle.status.value,
            options=[ft.DropdownOption(value.value, _status_label(value)) for value in CycleStatus],
        )
        message = ft.Text(ui_text("cycles.lifecycle_note"), color=tokens.text_muted, size=tokens.text_small)

        def save(_save_event) -> None:
            try:
                services.cycles.change_status.execute(cycle.id, CycleStatus(selected.value))
                close_dialog(page)
                show_success(page, tokens, ui_text("cycles.lifecycle_updated"))
                refresh()
            except Exception as error:
                message.value = ui_error(error)
                message.color = tokens.error.text
                message.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ui_text("cycles.lifecycle_title"),
                content=ft.Container(ft.Column([selected, message], spacing=tokens.space_3, tight=True), width=460),
                actions=dialog_footer(
                    ui_text("cycles.cancel"),
                    ui_text("cycles.save"),
                    lambda _e: close_dialog(page),
                    save,
                    tokens,
                ),
                bgcolor=tokens.surface_elevated,
            )
        )

    weekly_rows: list[ft.Control] = []
    for number in range(1, cycle.length_weeks + 1):
        item = outcomes.get(number)
        week_start, week_end = _week_dates(cycle.start_date, number)
        is_current = number == current_week
        title_value = item.title if item else ui_text("cycles.outcome_unplanned")
        row_controls: list[ft.Control] = [
            ft.Column(
                [
                    ft.Text(ui_text("cycles.week_number", number=number), color=tokens.accent_primary if is_current else tokens.text_primary, weight=ft.FontWeight.W_600),
                    ft.Text(ui_text("common.date_range", start=format_short_date(week_start), end=format_short_date(week_end)), color=tokens.text_muted, size=tokens.text_small),
                ],
                spacing=tokens.space_1,
                width=130,
            ),
            ft.Text(title_value, color=tokens.text_primary if item else tokens.text_muted, expand=True, max_lines=2),
        ]
        if item:
            row_controls.append(state_chip(_outcome_status_label(item.status), _outcome_status_color(item.status, tokens), tokens))
        else:
            row_controls.append(ft.Text(ui_text("cycles.not_set"), color=tokens.text_muted, size=tokens.text_small))
        if cycle.status is not CycleStatus.ARCHIVED:
            row_controls.append(ft.TextButton(ui_text("cycles.edit"), on_click=edit_week(number)))
        weekly_rows.append(
            ft.Container(
                ft.Row(row_controls, spacing=tokens.space_3, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=tokens.soft_red_background if is_current else tokens.surface_inner,
                border=ft.Border.all(tokens.border_width, tokens.accent_primary if is_current else tokens.border_default),
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
        )

    project_controls: list[ft.Control] = []
    for item in detail.project_summaries:
        project_controls.append(
            ft.Container(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item.project.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                                ft.Text(item.project.stage_label or ui_text("cycles.stage_not_set"), color=tokens.text_muted, size=tokens.text_small),
                                ft.Text(
                                    ui_text("cycles.project_milestone", value=item.current_milestone.title if item.current_milestone else ui_text("cycles.no_milestone_compact")),
                                    color=tokens.text_secondary,
                                    size=tokens.text_small,
                                ),
                                ft.Text(
                                    ui_text("cycles.project_open_tasks", count=item.open_task_count),
                                    color=tokens.text_muted,
                                    size=tokens.text_small,
                                ),
                            ],
                            spacing=tokens.space_1,
                            expand=True,
                        ),
                        ft.TextButton(ui_text("cycles.open_project"), on_click=lambda _e, project_id=item.project.id: navigate(f"/projects/{project_id}")),
                    ]
                ),
                bgcolor=tokens.surface_inner,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
        )
    milestone_project_titles = {item.project.id: item.project.title for item in detail.project_summaries}
    milestone_controls = [
        ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(item.title, color=tokens.text_primary, weight=ft.FontWeight.W_600, expand=True),
                            ft.Text(ui_text(f"cycles.milestone_status.{item.status.value}"), color=tokens.text_muted, size=tokens.text_small),
                        ]
                    ),
                    ft.Text(milestone_project_titles.get(item.project_id, ui_text("cycles.unknown_project")), color=tokens.text_muted, size=tokens.text_small),
                    ft.Text(item.definition_of_done, color=tokens.text_secondary, size=tokens.text_small),
                ],
                spacing=tokens.space_1,
            ),
            bgcolor=tokens.surface_inner,
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
        )
        for item in detail.milestones
    ]
    open_tasks = sum(item.task.lifecycle_status not in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED} for item in detail.tasks)
    completed_tasks = sum(item.task.lifecycle_status is TaskLifecycle.COMPLETED for item in detail.tasks)
    current_item = outcomes.get(current_week) if current_week else None
    if current_week:
        week_start, week_end = _week_dates(cycle.start_date, current_week)
        current_controls: list[ft.Control] = [
            ft.Text(ui_text("cycles.week_dates", number=current_week, start=format_short_date(week_start), end=format_short_date(week_end)), color=tokens.accent_primary, weight=ft.FontWeight.W_600),
            ft.Text(current_item.title if current_item else ui_text("cycles.outcome_unplanned"), color=tokens.text_primary),
            ft.Text(
                _outcome_status_label(current_item.status) if current_item else ui_text("cycles.not_set"),
                color=tokens.text_muted,
            ),
            ft.Text(ui_text("cycles.connected_work", projects=len(detail.projects), tasks=open_tasks), color=tokens.text_muted, size=tokens.text_small),
        ]
    else:
        current_controls = [ft.Text(ui_text("cycles.no_current_week"), color=tokens.text_muted)]
    progress_controls: list[ft.Control] = [
        ft.Text(
            ui_text("cycles.progress_fraction", achieved=achieved, planned=denominator)
            if denominator
            else ui_text("cycles.progress_unavailable"),
            color=tokens.text_primary,
            weight=ft.FontWeight.W_600,
        )
    ]
    if denominator:
        progress_controls.extend(
            [
                ft.ProgressBar(value=achieved / denominator, color=tokens.accent_primary, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
                ft.Text(
                    ui_text(
                        "cycles.detail_progress",
                        achieved=achieved,
                        partial=partial,
                        remaining=planned,
                        missed=not_achieved,
                        unplanned=cycle.length_weeks - denominator,
                    ),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                ),
            ]
        )
    return page_container(
        cycle.title,
        [
            card(ui_text("cycles.main_outcome"), [ft.Text(cycle.main_outcome, color=tokens.text_primary, size=tokens.text_emphasis)], tokens),
            ft.ResponsiveRow(
                [
                    card(ui_text("cycles.current_week"), current_controls, tokens, col={"sm": 12, "lg": 6}),
                    card(ui_text("cycles.weekly_progress"), progress_controls, tokens, col={"sm": 12, "lg": 6}),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
            card(ui_text("cycles.full_plan"), weekly_rows, tokens),
            ft.ResponsiveRow(
                [
                    card(ui_text("cycles.connected_projects"), project_controls or [empty_state(ui_text("cycles.no_projects"), tokens)], tokens, col={"sm": 12, "lg": 6}),
                    card(ui_text("cycles.milestones_section"), milestone_controls or [empty_state(ui_text("cycles.no_milestones"), tokens)], tokens, col={"sm": 12, "lg": 6}),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
            card(
                ui_text("cycles.connected_tasks"),
                [
                    ft.Text(ui_text("cycles.task_counts", open=open_tasks, completed=completed_tasks, total=len(detail.tasks)), color=tokens.text_primary),
                    ft.Text(ui_text("cycles.task_context_note"), color=tokens.text_muted, size=tokens.text_small),
                ] if detail.tasks else [empty_state(ui_text("cycles.no_tasks"), tokens)],
                tokens,
            ),
        ],
        tokens,
        subtitle=_date_range(cycle.start_date, cycle.end_date)
        + ((" - " + ui_text("cycles.week_of", week=current_week, length=cycle.length_weeks)) if current_week else ""),
        actions=[
            state_chip(_status_label(cycle.status), _cycle_status_color(cycle.status, tokens), tokens),
            ft.TextButton(ui_text("cycles.more"), on_click=open_lifecycle),
            ft.TextButton(ui_text("cycles.all_cycles"), on_click=lambda _e: navigate("/cycles")),
        ],
        content_spacing=tokens.space_5,
        page_id="cycles",
    )

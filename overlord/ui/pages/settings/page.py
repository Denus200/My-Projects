from __future__ import annotations

from collections.abc import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import primary_button, select_field, selection_button, text_field
from overlord.ui.state import AppSessionState
from overlord.ui.strings import ui_error, ui_text
from overlord.ui.components.layout import page_container
from overlord.ui.design_system.styles import selection_button_style
from overlord.ui.design_system.tokens import ThemeTokens


_CATEGORIES = ("appearance", "planning", "startup")


def _safe_update(control: ft.Control) -> None:
    try:
        control.update()
    except RuntimeError:
        # Presentation unit tests construct controls without mounting a Page.
        pass


def _section_heading(title: str, description: str, tokens: ThemeTokens) -> ft.Column:
    return ft.Column(
        [
            ft.Text(title, size=tokens.text_title, weight=ft.FontWeight.W_600, color=tokens.text_primary),
            ft.Text(description, size=tokens.text_body, color=tokens.text_secondary),
        ],
        spacing=tokens.space_1,
    )


def _setting_row(
    label: str,
    description: str,
    control: ft.Control,
    tokens: ThemeTokens,
) -> ft.Container:
    return ft.Container(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(label, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ft.Text(description, color=tokens.text_muted, size=tokens.text_small),
                    ],
                    spacing=tokens.space_1,
                    expand=True,
                ),
                control,
            ],
            spacing=tokens.space_4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        border=ft.Border.only(bottom=ft.BorderSide(tokens.border_width, tokens.border_default)),
        padding=ft.Padding.symmetric(vertical=tokens.space_3),
    )


def build_settings(
    services: ApplicationServices,
    tokens: ThemeTokens,
    apply_settings: Callable[..., None],
    report_error: Callable[[str], None],
    state: AppSessionState | None = None,
    page: ft.Page | None = None,
) -> ft.Control:
    settings = services.settings.get_settings.execute()
    session = state or AppSessionState(route="/settings")
    if session.settings_category not in _CATEGORIES:
        session.settings_category = "appearance"

    draft_theme = {"value": settings.theme_mode}
    motion = ft.Switch(value=settings.motion_enabled, tooltip=ui_text("settings.motion"))
    reduced = ft.Switch(value=settings.reduced_motion, tooltip=ui_text("settings.reduced_motion"))
    first_day = select_field(
        tokens,
        compact=True,
        value=settings.first_day_of_week,
        options=[
            ft.DropdownOption("monday", ui_text("settings.first_day.monday")),
            ft.DropdownOption("sunday", ui_text("settings.first_day.sunday")),
        ],
        width=220,
        tooltip=ui_text("settings.first_day"),
    )
    cycle_length = text_field(
        tokens,
        compact=True,
        value=str(settings.default_cycle_length),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
        tooltip=ui_text("settings.cycle_length"),
    )
    cycle_length_control = ft.Row(
        [cycle_length, ft.Text(ui_text("settings.weeks"), color=tokens.text_secondary)],
        spacing=tokens.space_2,
        tight=True,
    )
    startup = select_field(
        tokens,
        compact=True,
        value=settings.startup_destination,
        options=[
            ft.DropdownOption("dashboard", ui_text("nav.dashboard")),
            ft.DropdownOption("tasks", ui_text("nav.tasks")),
            ft.DropdownOption("projects", ui_text("nav.projects")),
            ft.DropdownOption("cycles", ui_text("nav.cycles")),
        ],
        width=240,
        tooltip=ui_text("settings.startup_destination"),
    )
    sidebar = ft.Switch(value=settings.sidebar_collapsed, tooltip=ui_text("settings.sidebar_collapsed"))
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    theme_buttons: dict[str, ft.Button] = {}

    def choose_theme(value: str):
        def choose(_event) -> None:
            draft_theme["value"] = value
            for theme_value, button in theme_buttons.items():
                selected = theme_value == value
                button.style = selection_button_style(tokens, selected=selected)
                _safe_update(button)

        return choose

    for value in ("system", "light", "dark"):
        selected = settings.theme_mode == value
        theme_buttons[value] = selection_button(
            ui_text(f"settings.theme.{value}"),
            tokens,
            selected=selected,
            tooltip=ui_text(f"settings.theme.{value}"),
            data=f"settings-theme-{value}",
            on_click=choose_theme(value),
        )

    def appearance_section() -> ft.Control:
        theme_control = ft.Row(list(theme_buttons.values()), spacing=tokens.space_2, wrap=True)
        return _settings_panel(
            ui_text("settings.category.appearance"),
            ui_text("settings.appearance.description"),
            [
                _setting_row(ui_text("settings.theme"), ui_text("settings.theme.description"), theme_control, tokens),
                _setting_row(ui_text("settings.motion"), ui_text("settings.motion.description"), motion, tokens),
                _setting_row(
                    ui_text("settings.reduced_motion"),
                    ui_text("settings.reduced_motion.description"),
                    reduced,
                    tokens,
                ),
                ft.Text(ui_text("settings.motion_effective_off"), color=tokens.text_muted, size=tokens.text_small),
            ],
            tokens,
        )

    def planning_section() -> ft.Control:
        return _settings_panel(
            ui_text("settings.category.planning"),
            ui_text("settings.planning.description"),
            [
                _setting_row(ui_text("settings.first_day"), ui_text("settings.first_day.description"), first_day, tokens),
                _setting_row(
                    ui_text("settings.cycle_length"),
                    ui_text("settings.cycle_length.description"),
                    cycle_length_control,
                    tokens,
                ),
            ],
            tokens,
        )

    def startup_section() -> ft.Control:
        return _settings_panel(
            ui_text("settings.category.startup"),
            ui_text("settings.startup.description"),
            [
                _setting_row(
                    ui_text("settings.startup_destination"),
                    ui_text("settings.startup_destination.description"),
                    startup,
                    tokens,
                ),
                _setting_row(
                    ui_text("settings.sidebar_collapsed"),
                    ui_text("settings.sidebar_collapsed.description"),
                    sidebar,
                    tokens,
                ),
            ],
            tokens,
        )

    builders = {
        "appearance": appearance_section,
        "planning": planning_section,
        "startup": startup_section,
    }
    content_host = ft.Container(content=builders[session.settings_category](), expand=True)
    category_buttons: dict[str, ft.Button] = {}
    category_selector = select_field(
        tokens,
        compact=True,
        label=ui_text("settings.category"),
        value=session.settings_category,
        options=[ft.DropdownOption(value, ui_text(f"settings.category.{value}")) for value in _CATEGORIES],
        width=320,
    )

    def select_category(value: str) -> None:
        session.settings_category = value if value in _CATEGORIES else "appearance"
        category_selector.value = session.settings_category
        content_host.content = builders[session.settings_category]()
        for category, button in category_buttons.items():
            selected = category == session.settings_category
            button.style = selection_button_style(tokens, selected=selected)
            _safe_update(button)
        _safe_update(category_selector)
        _safe_update(content_host)

    category_selector.on_select = lambda event: select_category(event.control.value or "appearance")
    for category in _CATEGORIES:
        selected = category == session.settings_category
        category_buttons[category] = selection_button(
            ui_text(f"settings.category.{category}"),
            tokens,
            selected=selected,
            width=190,
            data=f"settings-category-{category}",
            on_click=lambda _event, value=category: select_category(value),
        )

    save_button: ft.Button

    def save(_event) -> None:
        message.value = ""
        cycle_length.error = None
        save_button.disabled = True
        _safe_update(save_button)
        try:
            updated = services.settings.update_settings.execute(
                theme_mode=draft_theme["value"],
                motion_enabled=bool(motion.value),
                reduced_motion=bool(reduced.value),
                first_day_of_week=first_day.value,
                default_cycle_length=int(cycle_length.value or ""),
                startup_destination=startup.value,
                sidebar_collapsed=bool(sidebar.value),
            )
            apply_settings(updated, ui_text("settings.saved"))
        except ValueError as error:
            message.value = ui_error(error)
            message.color = tokens.error.text
            if isinstance(error, FieldValidationError) and error.field == "default_cycle_length":
                cycle_length.error = ui_error(error)
                _safe_update(cycle_length)
            _safe_update(message)
            save_button.disabled = False
            _safe_update(save_button)
        except Exception:
            report_error(ui_text("settings.save_error"))
            save_button.disabled = False
            _safe_update(save_button)

    save_button = primary_button(
        ui_text("settings.save"),
        tokens,
        on_click=save,
    )

    page_width = float(getattr(page, "width", 1280) or 1280)
    narrow = page_width < 1180
    category_rail = ft.Container(
        ft.Column(list(category_buttons.values()), spacing=tokens.space_2),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_3,
        width=214,
        visible=not narrow,
    )
    right_column = ft.Column(
        [
            ft.Container(category_selector, visible=narrow),
            content_host,
            message,
            ft.Row([save_button], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=tokens.space_4,
        expand=True,
    )
    settings_layout = ft.Row(
        [category_rail, right_column],
        spacing=tokens.space_5,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    return page_container(
        ui_text("settings.title"),
        [
            ft.Container(settings_layout, width=1000 if not narrow else None),
        ],
        tokens,
        subtitle=ui_text("settings.subtitle"),
        content_spacing=tokens.space_5,
        page_id="settings",
    )


def _settings_panel(
    title: str,
    description: str,
    controls: list[ft.Control],
    tokens: ThemeTokens,
) -> ft.Container:
    return ft.Container(
        ft.Column([_section_heading(title, description, tokens), *controls], spacing=tokens.space_3),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_5,
    )

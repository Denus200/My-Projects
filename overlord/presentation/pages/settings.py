from __future__ import annotations

import flet as ft

from overlord.application import ApplicationServices
from overlord.presentation.components.common import card, page_heading
from overlord.presentation.design_system.tokens import ThemeTokens


def build_settings(
    services: ApplicationServices,
    tokens: ThemeTokens,
    apply_settings,
    report_error,
) -> ft.Control:
    settings = services.settings.get_settings.execute()
    theme = ft.Dropdown(
        label="Theme",
        value=settings.theme_mode,
        options=[ft.DropdownOption("system", "System"), ft.DropdownOption("light", "Light"), ft.DropdownOption("dark", "Dark")],
    )
    motion = ft.Switch(label="Motion enabled", value=settings.motion_enabled)
    reduced = ft.Switch(label="Reduced motion", value=settings.reduced_motion)
    first_day = ft.Dropdown(
        label="First day of week",
        value=settings.first_day_of_week,
        options=[ft.DropdownOption("monday", "Monday"), ft.DropdownOption("sunday", "Sunday")],
    )
    cycle_length = ft.TextField(label="Default Cycle length", value=str(settings.default_cycle_length), keyboard_type=ft.KeyboardType.NUMBER)
    startup = ft.Dropdown(
        label="Startup destination",
        value=settings.startup_destination,
        options=[
            ft.DropdownOption("dashboard", "Dashboard"), ft.DropdownOption("tasks", "Tasks"),
            ft.DropdownOption("projects", "Projects"), ft.DropdownOption("cycles", "12-Week Plans"),
        ],
    )
    sidebar = ft.Switch(label="Start with sidebar collapsed", value=settings.sidebar_collapsed)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event):
        try:
            updated = services.settings.update_settings.execute(
                theme_mode=theme.value,
                motion_enabled=motion.value,
                reduced_motion=reduced.value,
                first_day_of_week=first_day.value,
                default_cycle_length=int(cycle_length.value),
                startup_destination=startup.value,
                sidebar_collapsed=sidebar.value,
            )
            apply_settings(updated)
        except Exception as error:
            message.value = str(error)
            message.update()

    preview = ft.ResponsiveRow([
        ft.Container(
            ft.Column([
                ft.Text("Light", color=tokens.text_primary, weight=ft.FontWeight.W_600),
                ft.Text("Warm surfaces with crimson focus.", color=tokens.text_secondary, size=tokens.text_small),
            ]),
            bgcolor=tokens.surface_elevated,
            border=ft.Border.all(tokens.focus_width if settings.theme_mode == "light" else tokens.border_width, tokens.accent_primary if settings.theme_mode == "light" else tokens.border_default),
            border_radius=tokens.radius_medium,
            padding=tokens.space_4,
            col={"sm": 12, "md": 6},
        ),
        ft.Container(
            ft.Column([
                ft.Text("Dark", color=tokens.text_primary, weight=ft.FontWeight.W_600),
                ft.Text("Deep neutral surfaces with restrained glow.", color=tokens.text_secondary, size=tokens.text_small),
            ]),
            bgcolor=tokens.surface_inner,
            border=ft.Border.all(tokens.focus_width if settings.theme_mode == "dark" else tokens.border_width, tokens.accent_primary if settings.theme_mode == "dark" else tokens.border_default),
            border_radius=tokens.radius_medium,
            padding=tokens.space_4,
            col={"sm": 12, "md": 6},
        ),
    ], spacing=tokens.space_3, run_spacing=tokens.space_3)
    return ft.Column([
        page_heading("Settings", "Appearance and planning defaults stay local to this device.", tokens),
        card("Appearance", [theme, preview, motion, reduced, ft.Text(
            "Effective motion is disabled whenever Reduced motion is on.", color=tokens.text_muted, size=tokens.text_small
        )], tokens),
        card("Planning", [first_day, cycle_length], tokens),
        card("Startup", [startup, sidebar], tokens),
        card("Future Widget", [ft.Text(
            "Widget defaults are reserved for the later read-only widget phase. No widget process is installed in v0.1.",
            color=tokens.text_muted,
        )], tokens),
        message,
        ft.Button("Save Settings", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=save),
    ], spacing=tokens.space_5, scroll=ft.ScrollMode.AUTO, expand=True)

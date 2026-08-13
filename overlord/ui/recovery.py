from __future__ import annotations

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


def build_recovery_view(
    tokens: ThemeTokens,
    *,
    error_id: str,
    database_path: str,
    category: str,
    error_type: str,
) -> ft.Control:
    return ft.Container(
        ft.Column([
            lucide_icon(
                IconName.ALERT,
                color=tokens.error.main,
                size=tokens.icon_display,
                label=ui_text("recovery.icon"),
            ),
            ft.Text(
                ui_text("recovery.title"),
                size=tokens.text_display,
                color=tokens.text_primary,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                ui_text("recovery.description"),
                color=tokens.text_secondary,
            ),
            ft.Text(ui_text("recovery.error_id", error_id=error_id), color=tokens.text_muted),
            ft.Text(ui_text("recovery.database", database_path=database_path), color=tokens.text_muted, selectable=True),
            ft.Text(ui_text("recovery.category", category=category), color=tokens.error.text),
            ft.Text(ui_text("recovery.error_type", error_type=error_type), color=tokens.text_muted),
            ft.Text(
                ui_text("recovery.guidance"),
                color=tokens.text_secondary,
            ),
        ], spacing=tokens.space_4),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_8,
        margin=tokens.space_8,
    )

from __future__ import annotations

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens


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
                label="Startup error",
            ),
            ft.Text(
                "Overlord could not open safely",
                size=tokens.text_display,
                color=tokens.text_primary,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                "Normal write actions are disabled. The database was not automatically recreated or restored.",
                color=tokens.text_secondary,
            ),
            ft.Text(f"Error ID: {error_id}", color=tokens.text_muted),
            ft.Text(f"Database: {database_path}", color=tokens.text_muted, selectable=True),
            ft.Text(f"Category: {category}", color=tokens.error.text),
            ft.Text(f"Error type: {error_type}", color=tokens.text_muted),
            ft.Text(
                "Review data/backups and docs/architecture/DATABASE_RECOVERY.md before restoring anything.",
                color=tokens.text_secondary,
            ),
        ], spacing=tokens.space_4),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_8,
        margin=tokens.space_8,
    )

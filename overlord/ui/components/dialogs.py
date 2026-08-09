from __future__ import annotations

from collections.abc import Callable

import flet as ft

from overlord.ui.design_system.tokens import ThemeTokens


def dialog_footer(
    cancel_label: str,
    primary_label: str,
    on_cancel: Callable[[object], None],
    on_primary: Callable[[object], None],
    tokens: ThemeTokens,
) -> list[ft.Control]:
    return [
        ft.TextButton(cancel_label, on_click=on_cancel),
        ft.Button(
            primary_label,
            bgcolor=tokens.accent_primary,
            color=tokens.on_accent,
            elevation=0,
            on_click=on_primary,
        ),
    ]


def close_dialog(page: ft.Page | None) -> None:
    if page is not None:
        page.pop_dialog()

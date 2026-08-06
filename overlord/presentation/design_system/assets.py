from __future__ import annotations

import flet as ft


def brand_mark(*, color: str, expanded: bool, title_size: int) -> ft.Control:
    return ft.Text(
        "Overlord" if expanded else "O",
        color=color,
        size=title_size,
        weight=ft.FontWeight.W_700,
        semantics_label="Overlord",
    )

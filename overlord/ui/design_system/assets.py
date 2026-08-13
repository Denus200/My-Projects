from __future__ import annotations

import flet as ft


def brand_mark(*, color: str, size: int) -> ft.Image:
    return ft.Image(
        src="brand/overlord-mark.svg",
        width=size,
        height=size,
        color=color,
        color_blend_mode=ft.BlendMode.SRC_IN,
        fit=ft.BoxFit.CONTAIN,
        anti_alias=True,
        semantics_label="Overlord",
    )

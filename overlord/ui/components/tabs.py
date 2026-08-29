from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens


@dataclass(frozen=True, slots=True)
class NavigationTab:
    key: str
    label: str
    icon: IconName


@dataclass(frozen=True, slots=True)
class SegmentedTab:
    key: str
    label: str
    width: int | float | None = None


@dataclass(frozen=True, slots=True)
class SegmentedDateNavigation:
    expanded: str | None
    on_toggle: Callable[[str], None]
    previous_label: str
    today_label: str
    next_label: str
    expand_label: Callable[[str], str]
    collapse_label: Callable[[str], str]
    on_previous: Callable[[], None]
    on_today: Callable[[], None]
    on_next: Callable[[], None]
    expandable_tabs: tuple[str, ...] = ("week", "month")


def _segmented_tab_style(
    tokens: ThemeTokens,
    *,
    active: bool,
    compact: bool = False,
) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color={ft.ControlState.DEFAULT: tokens.text_primary},
        bgcolor={
            ft.ControlState.HOVERED: tokens.interactive_hover,
            ft.ControlState.PRESSED: tokens.interactive_pressed,
            ft.ControlState.DEFAULT: (
                tokens.soft_red_background if active else ft.Colors.TRANSPARENT
            ),
        },
        overlay_color={ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
        side={
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
            ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
        },
        elevation=0,
        padding=ft.Padding.symmetric(
            horizontal=tokens.space_2 if compact else tokens.space_4
        ),
        shape=ft.RoundedRectangleBorder(radius=tokens.radius_small),
    )


def _date_navigation_action(
    label: str,
    action: str,
    width: int,
    tokens: ThemeTokens,
    on_click: Callable[[], None],
) -> ft.TextButton:
    primary = action == "today"
    return ft.TextButton(
        label,
        width=width,
        height=tokens.space_8,
        on_click=lambda _event: on_click(),
        style=ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: (
                    tokens.on_accent if primary else tokens.text_primary
                )
            },
            bgcolor={
                ft.ControlState.HOVERED: (
                    tokens.accent_primary_hover if primary else tokens.control_background_hover
                ),
                ft.ControlState.PRESSED: (
                    tokens.accent_primary_pressed if primary else tokens.interactive_pressed
                ),
                ft.ControlState.DEFAULT: (
                    tokens.accent_primary if primary else tokens.control_background
                ),
            },
            side={
                ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
                ft.ControlState.DEFAULT: ft.BorderSide(
                    0 if primary else tokens.border_width,
                    ft.Colors.TRANSPARENT if primary else tokens.border_default,
                ),
            },
            elevation=0,
            padding=ft.Padding.symmetric(horizontal=tokens.space_2),
            shape=ft.RoundedRectangleBorder(radius=tokens.space_2),
        ),
        data={"role": "segmented-tab-navigation-action", "action": action},
    )


def segmented_tabs(
    tabs: Sequence[SegmentedTab],
    selected: str,
    tokens: ThemeTokens,
    on_select: Callable[[str], None],
    *,
    width: int | float | None = None,
    role: str = "segmented-tabs",
    date_navigation: SegmentedDateNavigation | None = None,
) -> ft.Container:
    """Shared reference-aligned segmented Tabs control."""
    controls: list[ft.Control] = []
    for tab in tabs:
        active = tab.key == selected
        expandable = (
            active
            and date_navigation is not None
            and tab.key in date_navigation.expandable_tabs
        )
        if expandable:
            expanded = date_navigation.expanded == tab.key
            label_width = max(40, float(tab.width or 72) - (6 if expanded else 11))
            label_control = ft.TextButton(
                tab.label,
                width=label_width,
                height=44,
                on_click=lambda _event, key=tab.key: on_select(key),
                style=_segmented_tab_style(tokens, active=False, compact=True),
                data={"role": "segmented-tab-label", "tab": tab.key},
            )
            toggle_label = (
                date_navigation.collapse_label(tab.label)
                if expanded
                else date_navigation.expand_label(tab.label)
            )
            toggle = ft.TextButton(
                content=lucide_icon(
                    IconName.MINUS if expanded else IconName.PLUS,
                    color=tokens.text_primary,
                    size=tokens.icon_small,
                    label=toggle_label,
                    show_tooltip=False,
                ),
                width=tokens.space_8,
                height=tokens.space_8,
                on_click=lambda _event, key=tab.key: date_navigation.on_toggle(key),
                tooltip=toggle_label,
                style=ft.ButtonStyle(
                    bgcolor={
                        ft.ControlState.HOVERED: tokens.interactive_hover,
                        ft.ControlState.PRESSED: tokens.interactive_pressed,
                        ft.ControlState.DEFAULT: tokens.interactive_pressed,
                    },
                    overlay_color={ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
                    side={
                        ft.ControlState.FOCUSED: ft.BorderSide(
                            tokens.focus_width, tokens.focus_ring
                        ),
                        ft.ControlState.DEFAULT: ft.BorderSide(
                            0, ft.Colors.TRANSPARENT
                        ),
                    },
                    padding=tokens.space_0,
                    shape=ft.RoundedRectangleBorder(radius=tokens.space_2),
                ),
                data={
                    "role": "segmented-tab-navigation-toggle",
                    "tab": tab.key,
                    "expanded": expanded,
                },
            )
            group_controls: list[ft.Control] = [label_control, toggle]
            group_width = float(tab.width or 72) + 32
            if expanded:
                group_width = 354 if tab.key == "week" else 362
                group_controls.extend(
                    [
                        ft.Container(width=tokens.space_2),
                        _date_navigation_action(
                            date_navigation.previous_label,
                            "previous",
                            88,
                            tokens,
                            date_navigation.on_previous,
                        ),
                        _date_navigation_action(
                            date_navigation.today_label,
                            "today",
                            70,
                            tokens,
                            date_navigation.on_today,
                        ),
                        _date_navigation_action(
                            date_navigation.next_label,
                            "next",
                            64,
                            tokens,
                            date_navigation.on_next,
                        ),
                    ]
                )
            group_controls.append(ft.Container(expand=True))
            controls.append(
                ft.Container(
                    ft.Row(
                        group_controls,
                        spacing=tokens.space_1 if expanded else tokens.space_0,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=group_width,
                    height=44,
                    bgcolor=tokens.soft_red_background,
                    border_radius=tokens.radius_small,
                    data={
                        "role": "segmented-tab",
                        "tab": tab.key,
                        "selected": True,
                        "expandable": True,
                        "expanded": expanded,
                    },
                )
            )
            continue
        tab_width = tab.width
        if date_navigation is not None and date_navigation.expanded == "week" and tab.key == "month":
            tab_width = 74
        elif date_navigation is not None and date_navigation.expanded == "month" and tab.key == "week":
            tab_width = 66
        controls.append(
            ft.TextButton(
                tab.label,
                width=tab_width,
                height=44,
                on_click=lambda _event, key=tab.key: on_select(key),
                style=_segmented_tab_style(
                    tokens,
                    active=active,
                    compact=tab_width != tab.width,
                ),
                data={"role": "segmented-tab", "tab": tab.key, "selected": active},
            )
        )
    tabs_row = ft.Row(
        controls,
        spacing=tokens.space_0,
        tight=True,
        data={"role": role, "selected": selected},
    )
    return ft.Container(
        tabs_row,
        width=width,
        height=48,
        bgcolor=tokens.control_background,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.space_2,
        padding=ft.Padding.all(tokens.border_width),
        data={"role": "segmented-tabs-surface"},
    )


def navigation_tabs(
    tabs: Sequence[NavigationTab],
    selected: str,
    tokens: ThemeTokens,
    on_select: Callable[[str], None],
) -> ft.Container:
    """Shared baseline TabBar with stable active and hover geometry."""
    controls: list[ft.Control] = []
    for tab in tabs:
        active = tab.key == selected
        label_color = tokens.accent_primary if active else tokens.text_primary
        icon = lucide_icon(
            tab.icon,
            color=label_color,
            size=tokens.icon_small,
            label=tab.label,
            show_tooltip=False,
        )
        label = ft.Text(
            tab.label,
            color=label_color,
            size=tokens.text_body,
            weight=ft.FontWeight.W_500,
        )
        surface = ft.Container(
            ft.Row(
                [
                    icon,
                    label,
                ],
                spacing=tokens.space_2,
                tight=True,
            ),
            height=44,
            border=ft.Border.only(
                bottom=ft.BorderSide(
                    tokens.focus_width,
                    tokens.accent_primary if active else ft.Colors.TRANSPARENT,
                )
            ),
            padding=ft.Padding.symmetric(horizontal=tokens.space_4),
            alignment=ft.Alignment.CENTER,
            data={
                "role": "navigation-tab",
                "tab": tab.key,
                "selected": active,
                "stable_height": 44,
                "active_indicator": active,
            },
        )

        def hover(event: object, *, is_active: bool = active, tab_surface=surface, tab_icon=icon, tab_label=label) -> None:
            if is_active:
                return
            hovered = str(getattr(event, "data", "false")).lower() == "true"
            color = tokens.accent_primary_hover if hovered else tokens.text_primary
            tab_icon.color = color
            tab_label.color = color
            tab_surface.border = ft.Border.only(
                bottom=ft.BorderSide(
                    tokens.focus_width,
                    tokens.border_strong if hovered else ft.Colors.TRANSPARENT,
                )
            )
            try:
                tab_surface.update()
            except RuntimeError as error:
                if "Control must be added to the page first" not in str(error):
                    raise

        controls.append(
            ft.GestureDetector(
                surface,
                mouse_cursor=ft.MouseCursor.CLICK,
                on_tap=lambda _event, key=tab.key: on_select(key),
                on_hover=hover,
            )
        )
    return ft.Container(
        ft.Row(
            controls,
            spacing=tokens.space_1,
            scroll=ft.ScrollMode.HIDDEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
            data={"role": "project-tab-row", "selected": selected},
        ),
        height=45,
        border=ft.Border.only(bottom=ft.BorderSide(tokens.border_width, tokens.border_default)),
        data={
            "role": "project-tab-bar",
            "selected": selected,
            "baseline": True,
            "tab_height": 44,
        },
    )

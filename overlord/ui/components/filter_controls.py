from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
import math

import flet as ft

from overlord.ui.components.controls import checkbox, select_field, text_field
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import (
    UI_KIT_BLACK,
    UI_KIT_CONTROL_MUTED,
    UI_KIT_DISABLED_BORDER,
    UI_KIT_MENU_ITEM_HOVER,
    ThemeTokens,
)


@dataclass(frozen=True, slots=True)
class SelectOption:
    value: str
    label: str


def _safe_update(control: ft.Control) -> None:
    try:
        control.update()
    except RuntimeError as error:
        if "Control must be added to the page first" not in str(error):
            raise


def _chevron(tokens: ThemeTokens, *, open_state: bool = False) -> ft.Control:
    icon = lucide_icon(
        IconName.CHEVRON,
        color=tokens.text_primary,
        size=tokens.icon_small,
        label="",
        show_tooltip=False,
    )
    icon.rotate = ft.Rotate(angle=-math.pi / 2 if open_state else math.pi / 2)
    return icon


def search_box(
    tokens: ThemeTokens,
    *,
    hint: str,
    value: str = "",
    width: int | float = 599,
    on_change: Callable[[object], None] | None = None,
    on_submit: Callable[[object], None] | None = None,
) -> ft.TextField:
    """Canonical 599 x 48 Search control from the supplied UI kit."""
    return text_field(
        tokens,
        value=value,
        hint_text=hint,
        suffix_icon=ft.Container(
            lucide_icon(
                IconName.SEARCH,
                color=UI_KIT_CONTROL_MUTED,
                size=tokens.icon_small,
                label=hint,
            ),
            width=48,
            height=48,
            alignment=ft.Alignment.CENTER,
        ),
        suffix_icon_size_constraints=ft.BoxConstraints(
            min_width=48,
            max_width=48,
            min_height=48,
            max_height=48,
        ),
        width=width,
        height=48,
        border=ft.InputBorder.OUTLINE,
        border_radius=tokens.space_2,
        border_width=tokens.border_width,
        border_color=tokens.border_default,
        focused_border_width=tokens.border_width,
        focused_border_color=tokens.accent_primary,
        filled=True,
        fill_color=tokens.control_background,
        focused_bgcolor=tokens.control_background,
        hover_color=tokens.control_background_hover,
        color=tokens.text_primary,
        cursor_color=tokens.accent_primary,
        selection_color=tokens.interactive_selected,
        text_size=tokens.text_body,
        hint_style=ft.TextStyle(size=tokens.text_body, color=UI_KIT_CONTROL_MUTED),
        content_padding=ft.Padding.symmetric(horizontal=tokens.space_4, vertical=tokens.space_3),
        on_change=on_change,
        on_submit=on_submit,
        data={
            "role": "search",
            "reference_width": 599,
            "reference_height": 48,
            "icon_size": tokens.icon_small,
            "icon_stroke_reference": 1.5,
        },
    )


def _select_shell(
    tokens: ThemeTokens,
    *,
    label: str,
    width: int | float,
    count: int | None = None,
    open_state: bool = False,
) -> ft.Container:
    controls: list[ft.Control] = []
    if count is not None:
        controls.append(
            ft.Container(
                ft.Text(str(count), color=tokens.on_accent, size=tokens.text_body, weight=ft.FontWeight.W_600),
                width=24,
                height=24,
                bgcolor=UI_KIT_BLACK,
                border_radius=tokens.space_1,
                alignment=ft.Alignment.CENTER,
                data={"role": "multiselect-count", "count": count},
            )
        )
    controls.extend(
        [
            ft.Text(label, color=tokens.text_primary, size=tokens.text_body, expand=True, max_lines=1),
            _chevron(tokens, open_state=open_state),
        ]
    )
    return ft.Container(
        ft.Row(controls, spacing=tokens.space_2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        width=width,
        height=48,
        padding=ft.Padding.symmetric(horizontal=tokens.space_4),
        alignment=ft.Alignment.CENTER_LEFT,
    )


def _select_button_style(tokens: ThemeTokens) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        padding=0,
        bgcolor={
            ft.ControlState.HOVERED: tokens.control_background_hover,
            ft.ControlState.FOCUSED: tokens.control_background,
            ft.ControlState.DEFAULT: tokens.control_background,
        },
        overlay_color=ft.Colors.TRANSPARENT,
        side={
            ft.ControlState.HOVERED: ft.BorderSide(tokens.border_width, tokens.accent_primary),
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.border_width, tokens.accent_primary),
            ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, tokens.border_default),
        },
        shape=ft.RoundedRectangleBorder(radius=tokens.space_2),
        mouse_cursor=ft.MouseCursor.CLICK,
    )


def _popup_menu_style(
    tokens: ThemeTokens,
    *,
    width: int | float,
    max_height: int | float,
) -> ft.MenuStyle:
    return ft.MenuStyle(
        bgcolor=tokens.surface_elevated,
        elevation=2,
        padding=0,
        side=ft.BorderSide(tokens.border_width, tokens.border_default),
        shape=ft.RoundedRectangleBorder(radius=tokens.space_2),
        max_size=ft.Size(width, max_height),
        mouse_cursor=ft.MouseCursor.CLICK,
    )


def filter_checkbox(
    tokens: ThemeTokens,
    *,
    value: bool,
    label: str,
    disabled: bool = False,
) -> ft.Checkbox:
    """Reusable 24px Checkbox matching the supplied Cheak_box component."""
    return checkbox(
        tokens,
        value=value,
        disabled=disabled,
        width=24,
        height=24,
        fill_color={
            ft.ControlState.DISABLED: tokens.control_background_disabled,
            ft.ControlState.SELECTED: UI_KIT_BLACK,
            ft.ControlState.HOVERED: tokens.control_background,
            ft.ControlState.DEFAULT: tokens.control_background,
        },
        check_color=tokens.on_accent,
        overlay_color=ft.Colors.TRANSPARENT,
        border_side={
            ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, UI_KIT_DISABLED_BORDER),
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.border_width, tokens.accent_primary),
            ft.ControlState.SELECTED: ft.BorderSide(tokens.border_width, UI_KIT_BLACK),
            ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, UI_KIT_BLACK),
        },
        shape=ft.RoundedRectangleBorder(radius=tokens.space_1),
        semantics_label=label,
        data={"role": "filter-checkbox", "checked": value, "label": label},
    )


class Multiselect:
    """Native submenu-backed checkbox multiselect with count and open states."""

    def __init__(
        self,
        tokens: ThemeTokens,
        *,
        label: str,
        options: Iterable[SelectOption],
        selected: Iterable[str] = (),
        width: int | float = 142,
        menu_width: int | float | None = None,
        max_menu_height: int | float = 320,
        singular_label: str | None = None,
        on_change: Callable[[set[str]], None] | None = None,
        role: str = "multiselect",
    ) -> None:
        self.tokens = tokens
        self.label = label
        self.options = tuple(options)
        self.selected = set(selected)
        self.width = width
        self.menu_width = menu_width or max(width, 220)
        self.max_menu_height = max_menu_height
        self.singular_label = singular_label
        self.on_change = on_change
        self.role = role
        self.open = False
        self.control = ft.SubmenuButton(
            content=self._trigger_content(False),
            controls=self._items(),
            width=width,
            height=48,
            style=_select_button_style(tokens),
            menu_style=_popup_menu_style(tokens, width=self.menu_width, max_height=max_menu_height),
            on_open=lambda _event: self._set_open(True),
            on_close=lambda _event: self._set_open(False),
            data=self._data(),
        )

    def _display_label(self) -> str:
        if len(self.selected) == 1 and self.singular_label:
            return self.singular_label
        return self.label

    def _trigger_content(self, open_state: bool) -> ft.Container:
        surface = _select_shell(
            self.tokens,
            label=self._display_label(),
            width=self.width,
            count=len(self.selected),
            open_state=open_state,
        )
        surface.data = {"role": f"{self.role}-trigger", "count": len(self.selected)}
        return surface

    def _item(self, option: SelectOption) -> ft.MenuItemButton:
        checked = option.value in self.selected
        visual = ft.Container(
            ft.Row(
                [
                    ft.TransparentPointer(
                        filter_checkbox(self.tokens, value=checked, label=option.label),
                        width=24,
                        height=24,
                    ),
                    ft.Text(
                        option.label,
                        size=self.tokens.text_body,
                        color=self.tokens.text_primary,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True,
                    ),
                ],
                spacing=self.tokens.space_2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=self.menu_width,
            height=40,
            padding=ft.Padding.symmetric(horizontal=self.tokens.space_4),
            alignment=ft.Alignment.CENTER_LEFT,
        )
        return ft.MenuItemButton(
            content=visual,
            close_on_click=False,
            width=self.menu_width,
            height=40,
            semantic_label=option.label,
            style=ft.ButtonStyle(
                padding=0,
                bgcolor={
                    ft.ControlState.HOVERED: UI_KIT_MENU_ITEM_HOVER,
                    ft.ControlState.FOCUSED: UI_KIT_MENU_ITEM_HOVER,
                    ft.ControlState.DEFAULT: self.tokens.surface_elevated,
                },
                overlay_color=ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=0),
                mouse_cursor=ft.MouseCursor.CLICK,
            ),
            on_click=lambda _event, value=option.value: self._choose(value, value not in self.selected),
            data={
                "role": "multiselect-option",
                "value": option.value,
                "label": option.label,
                "checked": checked,
            },
        )

    def _items(self) -> list[ft.Control]:
        controls: list[ft.Control] = []
        for index, option in enumerate(self.options):
            controls.append(self._item(option))
            if index < len(self.options) - 1:
                controls.append(ft.Divider(height=1, thickness=1, color=self.tokens.border_default))
        return controls

    def _data(self) -> dict[str, object]:
        return {
            "role": self.role,
            "selected": sorted(self.selected),
            "open": self.open,
            "option_count": len(self.options),
            "options": tuple((option.value, option.label) for option in self.options),
            "max_menu_height": self.max_menu_height,
            "selection_mode": "multiple",
        }

    def _choose(self, value: str, checked: bool) -> None:
        if checked:
            self.selected.add(value)
        else:
            self.selected.discard(value)
        self._refresh()
        if self.on_change is not None:
            self.on_change(set(self.selected))

    def set_selected(self, selected: Iterable[str]) -> None:
        self.selected = set(selected)
        self._refresh()

    def _set_open(self, open_state: bool) -> None:
        self.open = open_state
        self.control.content = self._trigger_content(open_state)
        self.control.data = self._data()
        _safe_update(self.control)

    def _refresh(self) -> None:
        self.control.content = self._trigger_content(self.open)
        self.control.controls = self._items()
        self.control.data = self._data()
        _safe_update(self.control)


def toolbar_menu_bar(
    tokens: ThemeTokens,
    controls: Sequence[ft.Control],
    *,
    role: str = "toolbar-menu-bar",
) -> ft.MenuBar:
    """Groups toolbar submenus so only one related menu stays open."""
    return ft.MenuBar(
        controls=list(controls),
        clip_behavior=ft.ClipBehavior.NONE,
        style=ft.MenuStyle(
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
            padding=0,
            side=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            shape=ft.RoundedRectangleBorder(radius=0),
        ),
        data={"role": role, "exclusive_open": True},
    )


def single_select(
    tokens: ThemeTokens,
    *,
    value: str,
    options: Iterable[SelectOption],
    width: int | float,
    on_select: Callable[[str], None],
    role: str = "single-select",
) -> ft.Dropdown:
    """Canonical single-select Dropdown using the supplied 48px shell states."""
    resolved = tuple(options)
    labels = {option.value: option.label for option in resolved}

    def choose(event: object) -> None:
        selected = str(getattr(getattr(event, "control", None), "value", value))
        on_select(selected)

    return select_field(
        tokens,
        searchable=False,
        value=value,
        options=[
            ft.DropdownOption(
                key=option.value,
                text=option.label,
                data={"role": "single-select-option", "value": option.value},
            )
            for option in resolved
        ],
        width=width,
        height=48,
        editable=False,
        border=ft.InputBorder.OUTLINE,
        border_radius=tokens.space_2,
        border_width=tokens.border_width,
        border_color=tokens.border_default,
        focused_border_width=tokens.border_width,
        focused_border_color=tokens.accent_primary,
        filled=True,
        fill_color=tokens.control_background,
        hover_color=tokens.control_background_hover,
        color=tokens.text_primary,
        text_size=tokens.text_body,
        content_padding=ft.Padding.symmetric(horizontal=tokens.space_4),
        trailing_icon=_chevron(tokens, open_state=False),
        selected_trailing_icon=_chevron(tokens, open_state=True),
        menu_height=320,
        menu_width=width,
        menu_style=_popup_menu_style(tokens, width=width, max_height=320),
        on_select=choose,
        data={
            "role": role,
            "value": value,
            "label": labels[value],
            "options": tuple((option.value, option.label) for option in resolved),
            "selection_mode": "single",
        },
    )

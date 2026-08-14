from __future__ import annotations

import re
import unittest
from pathlib import Path

import flet as ft

from overlord.ui.components.controls import (
    checkbox,
    choice_chip,
    data_table,
    primary_button,
    secondary_button,
    select_field,
    selection_button,
    tertiary_button,
    text_field,
)
from overlord.ui.design_system.themes import build_dark_theme, build_light_theme
from overlord.ui.design_system.tokens import DARK_TOKENS, LIGHT_TOKENS


ROOT = Path(__file__).resolve().parents[1]


def _relative_luminance(value: str) -> float:
    channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    light, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class DesignSystemTests(unittest.TestCase):
    def test_theme_semantic_color_contract_is_characterized(self):
        expected = {
            "app_background": ("#0E0F13", "#FAF7F5"),
            "app_bar": ("#11131A", "#FFFFFF"),
            "surface_card": ("#151720", "#FFFFFF"),
            "surface_inner": ("#1A1D28", "#F7F2F4"),
            "surface_elevated": ("#1C1F2B", "#FFFDFC"),
            "border_default": ("#2A2E3A", "#E5DDE2"),
            "border_strong": ("#3A4050", "#D4C8D0"),
            "text_primary": ("#F5F3F7", "#17131A"),
            "text_secondary": ("#A6A3B0", "#6F6472"),
            "text_muted": ("#75727E", "#918793"),
            "accent_primary": ("#E11D48", "#D61F45"),
            "accent_primary_hover": ("#F43F5E", "#B9143A"),
            "accent_primary_pressed": ("#BE123C", "#8F1235"),
            "accent_primary_disabled": ("#6B2A3A", "#D8AEB9"),
            "accent_bright": ("#FF3B5C", "#FF3B5C"),
            "on_accent": ("#FFFFFF", "#FFFFFF"),
            "focus_ring": ("#FB7185", "#7F1D3A"),
            "interactive_hover": ("#202430", "#FFF1F4"),
            "interactive_pressed": ("#292E3D", "#F9DCE4"),
            "interactive_selected": ("#3A111C", "#FFE5EC"),
            "control_background": ("#151720", "#FFFFFF"),
            "control_background_hover": ("#1A1D28", "#FFFAFB"),
            "control_background_disabled": ("#11131A", "#F1ECEF"),
            "text_disabled": ("#66626D", "#AAA0A7"),
            "dashboard_add_background": ("#F1F1F1", "#F1F1F1"),
            "dashboard_add_border": ("#E9E9E9", "#E9E9E9"),
            "dashboard_add_text": ("#9A9A9A", "#9A9A9A"),
            "dashboard_add_icon": ("#000000", "#000000"),
            "dashboard_add_disabled_background": ("#ECECEC", "#ECECEC"),
            "dashboard_add_disabled_border": ("#E7E7E7", "#E7E7E7"),
            "dashboard_add_disabled_text": ("#DDDDDD", "#DDDDDD"),
            "dashboard_completion_border": ("#3A4050", "#DDDDDD"),
            "dashboard_completion_fill": ("#2ED17C", "#12C933"),
            "dashboard_completion_fill_border": ("#238A57", "#47A958"),
            "dashboard_completion_check": ("#D9FFE6", "#D9FFE6"),
            "profile_trigger_background": ("#FFFFFF", "#FFFFFF"),
            "profile_trigger_foreground": ("#000000", "#000000"),
            "sidebar_foreground": ("#F5F3F7", "#37303A"),
            "sidebar_border": ("#2A2E3A", "#ECE8EB"),
            "sidebar_active_border": ("#BE123C", "#BF0F34"),
            "sidebar_hover_border": ("#7F1D32", "#FFD8E2"),
            "toggle_track_default": ("#3A4050", "#D4C8D0"),
            "toggle_track_hover": ("#4A5060", "#C1AEBB"),
            "toggle_track_pressed": ("#596071", "#AF98A7"),
            "scrim": ("#99000000", "#99000000"),
            "soft_red_background": ("#3A111C", "#FFE5EC"),
            "soft_red_border": ("#7F1D32", "#FFC2D0"),
            "soft_red_text": ("#FFB3C1", "#9F1239"),
            "tertiary_foreground": ("#E11D48", "#0F766E"),
            "tertiary_foreground_hover": ("#E11D48", "#115E56"),
            "tertiary_foreground_pressed": ("#E11D48", "#134E4A"),
            "selection_foreground": ("#E11D48", "#0F766E"),
            "selection_foreground_hover": ("#F43F5E", "#115E56"),
            "selection_foreground_pressed": ("#BE123C", "#134E4A"),
            "selection_surface_hover": ("#202430", "#EAF6F4"),
            "selection_surface_pressed": ("#292E3D", "#C7E7E3"),
            "selection_surface_selected": ("#3A111C", "#D3EEEA"),
            "theme_secondary": ("#FF7AB6", "#0F766E"),
        }
        for name, values in expected.items():
            with self.subTest(name=name):
                self.assertEqual(values, (getattr(DARK_TOKENS, name), getattr(LIGHT_TOKENS, name)))

        expected_states = {
            "success": (("#2ED17C", "#0B2A1A", "#86EFAC"), ("#16A34A", "#DCFCE7", "#166534")),
            "warning": (("#F4B740", "#30230A", "#FCD34D"), ("#D97706", "#FEF3C7", "#92400E")),
            "blocker": (("#A78BFA", "#24163F", "#C4B5FD"), ("#7C3AED", "#EDE9FE", "#5B21B6")),
            "info": (("#5A8DFF", "#10213F", "#93C5FD"), ("#2563EB", "#DBEAFE", "#1D4ED8")),
            "neutral": (("#8B95A5", "#1C2430", "#CBD5E1"), ("#64748B", "#F1F5F9", "#475569")),
            "error": (("#FF4444", "#3B1114", "#FCA5A5"), ("#DC2626", "#FEE2E2", "#991B1B")),
        }
        for name, values in expected_states.items():
            with self.subTest(name=name):
                dark = getattr(DARK_TOKENS, name)
                light = getattr(LIGHT_TOKENS, name)
                self.assertEqual(values, ((dark.main, dark.background, dark.text), (light.main, light.background, light.text)))

    def test_theme_and_explicit_factories_share_checkbox_and_chip_state_values(self):
        for tokens, build_theme in ((LIGHT_TOKENS, build_light_theme), (DARK_TOKENS, build_dark_theme)):
            with self.subTest(theme=tokens.app_background):
                theme = build_theme()
                explicit_checkbox = checkbox(tokens, label="Complete")
                explicit_chip = choice_chip("Filter", tokens, selected=True)

                self.assertEqual(explicit_checkbox.fill_color, theme.checkbox_theme.fill_color)
                self.assertEqual(explicit_checkbox.overlay_color, theme.checkbox_theme.overlay_color)
                self.assertEqual(explicit_checkbox.check_color, theme.checkbox_theme.check_color)
                self.assertEqual(
                    explicit_checkbox.border_side[ft.ControlState.DEFAULT],
                    theme.checkbox_theme.border_side,
                )
                self.assertEqual(explicit_chip.bgcolor, theme.chip_theme.bgcolor)
                self.assertEqual(explicit_chip.selected_color, theme.chip_theme.selected_color)
                self.assertEqual(explicit_chip.disabled_color, theme.chip_theme.disabled_color)
                self.assertEqual(
                    explicit_chip.color[ft.ControlState.SELECTED],
                    theme.chip_theme.color[ft.ControlState.SELECTED],
                )
                self.assertEqual(explicit_chip.check_color, theme.chip_theme.check_color)

    def test_selection_roles_are_total_and_legacy_fallback_fields_are_retired(self):
        required = (
            "tertiary_foreground",
            "tertiary_foreground_hover",
            "tertiary_foreground_pressed",
            "selection_foreground",
            "selection_foreground_hover",
            "selection_foreground_pressed",
            "selection_surface_hover",
            "selection_surface_pressed",
            "selection_surface_selected",
            "theme_secondary",
        )
        retired = (
            "accent_alt",
            "interactive_hover_alt",
            "interactive_pressed_alt",
            "interactive_selected_alt",
            "pink_accent",
            "soft_teal_background",
        )
        for tokens in (LIGHT_TOKENS, DARK_TOKENS):
            with self.subTest(theme=tokens.app_background):
                self.assertTrue(all(getattr(tokens, name) is not None for name in required))
                self.assertTrue(all(not hasattr(tokens, name) for name in retired))

    def test_light_theme_core_pairs_meet_wcag_aa(self):
        self.assertGreaterEqual(_contrast(LIGHT_TOKENS.text_primary, LIGHT_TOKENS.app_background), 4.5)
        self.assertGreaterEqual(_contrast(LIGHT_TOKENS.text_secondary, LIGHT_TOKENS.app_background), 4.5)
        self.assertGreaterEqual(_contrast(LIGHT_TOKENS.on_accent, LIGHT_TOKENS.accent_primary), 4.5)
        self.assertGreaterEqual(_contrast(LIGHT_TOKENS.focus_ring, LIGHT_TOKENS.control_background), 3.0)

    def test_light_selection_roles_match_approved_values_and_contrast(self):
        self.assertEqual(
            (
                "#0F766E", "#115E56", "#134E4A",
                "#0F766E", "#115E56", "#134E4A",
                "#EAF6F4", "#C7E7E3", "#D3EEEA", "#0F766E",
            ),
            (
                LIGHT_TOKENS.tertiary_foreground,
                LIGHT_TOKENS.tertiary_foreground_hover,
                LIGHT_TOKENS.tertiary_foreground_pressed,
                LIGHT_TOKENS.selection_foreground,
                LIGHT_TOKENS.selection_foreground_hover,
                LIGHT_TOKENS.selection_foreground_pressed,
                LIGHT_TOKENS.selection_surface_hover,
                LIGHT_TOKENS.selection_surface_pressed,
                LIGHT_TOKENS.selection_surface_selected,
                LIGHT_TOKENS.theme_secondary,
            ),
        )
        self.assertGreaterEqual(_contrast(LIGHT_TOKENS.selection_foreground, LIGHT_TOKENS.app_background), 4.5)

    def test_light_alt_palette_drives_links_filters_chips_and_secondary_scheme(self):
        tertiary = tertiary_button("More", LIGHT_TOKENS)
        selection = selection_button("Appearance", LIGHT_TOKENS, selected=True)
        chip = choice_chip("Filter", LIGHT_TOKENS, selected=True)
        table = data_table(
            [ft.DataColumn(label="Task")],
            [ft.DataRow(cells=[ft.DataCell("Review")])],
            LIGHT_TOKENS,
        )
        theme = build_light_theme()

        self.assertEqual(LIGHT_TOKENS.tertiary_foreground, tertiary.style.color[ft.ControlState.DEFAULT])
        self.assertEqual(LIGHT_TOKENS.tertiary_foreground_hover, tertiary.style.color[ft.ControlState.HOVERED])
        self.assertEqual(LIGHT_TOKENS.selection_surface_hover, tertiary.style.bgcolor[ft.ControlState.HOVERED])
        self.assertEqual(LIGHT_TOKENS.selection_foreground, selection.style.color[ft.ControlState.DEFAULT])
        self.assertEqual(LIGHT_TOKENS.selection_surface_selected, selection.style.bgcolor[ft.ControlState.DEFAULT])
        self.assertEqual(LIGHT_TOKENS.selection_foreground, chip.check_color)
        self.assertEqual(LIGHT_TOKENS.selection_surface_selected, chip.selected_color)
        self.assertEqual(LIGHT_TOKENS.selection_surface_hover, table.data_row_color[ft.ControlState.HOVERED])
        self.assertEqual(LIGHT_TOKENS.theme_secondary, theme.color_scheme.secondary)

    def test_dark_theme_keeps_pre_alt_rendered_colors(self):
        tertiary = tertiary_button("More", DARK_TOKENS)
        selection = selection_button("Appearance", DARK_TOKENS, selected=True)
        chip = choice_chip("Filter", DARK_TOKENS, selected=True)
        theme = build_dark_theme()

        self.assertEqual("#E11D48", DARK_TOKENS.tertiary_foreground)
        self.assertEqual("#E11D48", DARK_TOKENS.tertiary_foreground_hover)
        self.assertEqual("#E11D48", DARK_TOKENS.tertiary_foreground_pressed)
        self.assertEqual("#E11D48", DARK_TOKENS.selection_foreground)
        self.assertEqual("#F43F5E", DARK_TOKENS.selection_foreground_hover)
        self.assertEqual("#BE123C", DARK_TOKENS.selection_foreground_pressed)
        self.assertEqual("#202430", DARK_TOKENS.selection_surface_hover)
        self.assertEqual("#292E3D", DARK_TOKENS.selection_surface_pressed)
        self.assertEqual("#3A111C", DARK_TOKENS.selection_surface_selected)
        self.assertEqual("#FF7AB6", DARK_TOKENS.theme_secondary)
        self.assertEqual("#E11D48", tertiary.style.color[ft.ControlState.DEFAULT])
        self.assertEqual("#202430", tertiary.style.bgcolor[ft.ControlState.HOVERED])
        self.assertEqual("#E11D48", selection.style.color[ft.ControlState.DEFAULT])
        self.assertEqual("#3A111C", selection.style.bgcolor[ft.ControlState.DEFAULT])
        self.assertEqual("#E11D48", chip.check_color)
        self.assertEqual("#3A111C", chip.selected_color)
        self.assertEqual("#FF7AB6", theme.color_scheme.secondary)

    def test_primary_and_secondary_buttons_have_distinct_interaction_states(self):
        primary = primary_button("Save", LIGHT_TOKENS)
        secondary = secondary_button("Cancel", LIGHT_TOKENS)

        self.assertEqual(LIGHT_TOKENS.control_height, primary.height)
        self.assertNotEqual(
            primary.style.bgcolor[ft.ControlState.DEFAULT],
            primary.style.bgcolor[ft.ControlState.HOVERED],
        )
        self.assertNotEqual(
            primary.style.bgcolor[ft.ControlState.HOVERED],
            primary.style.bgcolor[ft.ControlState.PRESSED],
        )
        self.assertNotEqual(
            secondary.style.bgcolor[ft.ControlState.DEFAULT],
            secondary.style.bgcolor[ft.ControlState.HOVERED],
        )
        self.assertEqual(LIGHT_TOKENS.focus_width, primary.style.side[ft.ControlState.FOCUSED].width)
        self.assertEqual(ft.MouseCursor.FORBIDDEN, primary.style.mouse_cursor[ft.ControlState.DISABLED])

    def test_reduced_motion_removes_button_transition_duration(self):
        normal = build_light_theme(motion_enabled=True)
        reduced = build_light_theme(motion_enabled=False)
        self.assertEqual(LIGHT_TOKENS.motion_fast, normal.button_theme.style.animation_duration)
        self.assertEqual(LIGHT_TOKENS.motion_none, reduced.button_theme.style.animation_duration)

    def test_inputs_and_selects_share_geometry_and_focus_treatment(self):
        field = text_field(LIGHT_TOKENS, label="Title")
        select = select_field(
            LIGHT_TOKENS,
            label="Project",
            options=[ft.DropdownOption("one", "One")],
        )
        self.assertEqual(LIGHT_TOKENS.radius_medium, field.border_radius)
        self.assertEqual(field.border_radius, select.border_radius)
        self.assertEqual(LIGHT_TOKENS.focus_ring, field.focused_border_color)
        self.assertEqual(field.focused_border_color, select.focused_border_color)
        self.assertEqual(field.content_padding, select.content_padding)
        self.assertEqual(LIGHT_TOKENS.control_background_hover, field.hover_color)
        self.assertEqual(LIGHT_TOKENS.control_background_hover, select.hover_color)

    def test_choice_chip_is_visible_before_hover_and_selected_without_color_alone(self):
        chip = choice_chip("Primary", LIGHT_TOKENS, selected=True)
        self.assertEqual(LIGHT_TOKENS.control_background, chip.bgcolor)
        self.assertEqual(LIGHT_TOKENS.selection_surface_selected, chip.selected_color)
        self.assertEqual(LIGHT_TOKENS.border_strong, chip.border_side.color)
        self.assertTrue(chip.show_checkmark)
        self.assertEqual(LIGHT_TOKENS.selection_foreground, chip.check_color)

    def test_basic_data_table_uses_shared_density_and_state_colors(self):
        table = data_table(
            [ft.DataColumn(label="Task")],
            [ft.DataRow(cells=[ft.DataCell("Review")])],
            LIGHT_TOKENS,
        )
        self.assertEqual(LIGHT_TOKENS.table_heading_height, table.heading_row_height)
        self.assertEqual(LIGHT_TOKENS.table_row_height, table.data_row_min_height)
        self.assertEqual(LIGHT_TOKENS.selection_surface_hover, table.data_row_color[ft.ControlState.HOVERED])
        self.assertEqual(LIGHT_TOKENS.selection_surface_selected, table.data_row_color[ft.ControlState.SELECTED])

    def test_active_ui_uses_shared_form_factories(self):
        controls_path = ROOT / "overlord" / "ui" / "components" / "controls.py"
        for path in (ROOT / "overlord" / "ui").rglob("*.py"):
            if path == controls_path:
                continue
            source = path.read_text(encoding="utf-8")
            direct = re.findall(r"ft\.(?:TextField|Dropdown|Checkbox)\(", source)
            self.assertEqual([], direct, path)

    def test_no_parallel_generated_master_design_system_exists(self):
        self.assertFalse((ROOT / "design-system").exists())


if __name__ == "__main__":
    unittest.main()

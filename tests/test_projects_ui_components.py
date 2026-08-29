from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import flet as ft

from overlord.ui.components.filter_controls import (
    Multiselect,
    SelectOption,
    filter_checkbox,
    search_box,
    single_select,
)
from overlord.ui.components.project_cards import (
    PROJECT_CARD_COLLAPSED_WIDTH,
    PROJECT_CARD_EXPANDED_WIDTH,
    ProjectCardShell,
    darken_color,
    project_metric_chip,
)
from overlord.ui.components.project_overview import (
    ProjectActivityItem,
    ProjectActivityKind,
    StageTimelineItem,
    recent_project_activity,
    stage_progress_timeline,
)
from overlord.ui.components.status import StatusBadgeFill, StatusBadgeSize, status_badge
from overlord.ui.design_system.tokens import LIGHT_TOKENS


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control, role: str):
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class ProjectsUiComponentTests(unittest.TestCase):
    def test_project_card_shell_preserves_fixed_notch_geometry_in_both_width_states(self):
        expanded = ProjectCardShell(PROJECT_CARD_EXPANDED_WIDTH, "#FFC7D2", LIGHT_TOKENS)
        collapsed = ProjectCardShell(PROJECT_CARD_COLLAPSED_WIDTH, "#FFC7D2", LIGHT_TOKENS)
        self.assertEqual(401, expanded.control.data["width"])
        self.assertEqual(354, collapsed.control.data["width"])
        self.assertEqual(expanded.control.data["notch_width"], collapsed.control.data["notch_width"])
        self.assertEqual(66, expanded.control.data["notch_width"])
        self.assertEqual("#E6B3BD", darken_color("#FFC7D2"))

    def test_project_metric_chip_uses_card_tint_overlays_not_status_colors(self):
        chip = project_metric_chip("3 open tasks", LIGHT_TOKENS)
        self.assertEqual(26, chip.height)
        self.assertEqual("#0A000000", chip.bgcolor)
        self.assertEqual(0.04, chip.data["overlay_opacity"])
        self.assertEqual(0.16, chip.data["border_opacity"])

    def test_status_badge_exposes_canonical_status_size_and_fill_variants(self):
        badge = status_badge(
            "blocked",
            "Blocked",
            LIGHT_TOKENS,
            size=StatusBadgeSize.SMALL,
            fill=StatusBadgeFill.SUBTLE,
        )
        self.assertEqual("blocked", badge.data["status"])
        self.assertEqual("small", badge.data["size"])
        self.assertEqual("subtle", badge.data["fill"])
        self.assertEqual(24, badge.height)

    def test_search_and_multiselect_match_reference_control_geometry_and_selection(self):
        search = search_box(LIGHT_TOKENS, hint="Search Tasks or Projects...")
        self.assertEqual(599, search.width)
        self.assertEqual(48, search.height)
        self.assertEqual(16, search.data["icon_size"])
        self.assertEqual(LIGHT_TOKENS.accent_primary, search.focused_border_color)
        self.assertEqual(LIGHT_TOKENS.border_width, search.focused_border_width)
        changes: list[set[str]] = []
        multiselect = Multiselect(
            LIGHT_TOKENS,
            label="Projects",
            singular_label="Project",
            options=(SelectOption("1", "Project One"), SelectOption("2", "Project Two")),
            menu_width=260,
            on_change=changes.append,
        )
        option = next(item for item in _role(multiselect.control, "multiselect-option") if item.data["value"] == "1")
        with patch.object(ft.Control, "update", lambda _control: None):
            option.on_click(None)
        self.assertEqual({"1"}, multiselect.selected)
        self.assertEqual([{"1"}], changes)
        self.assertEqual(1, _role(multiselect.control, "multiselect-count")[0].data["count"])
        self.assertEqual("Project", _role(multiselect.control, "multiselect-trigger")[0].content.controls[1].value)
        self.assertEqual(2, multiselect.control.data["option_count"])
        self.assertEqual(320, multiselect.control.data["max_menu_height"])
        self.assertFalse(option.close_on_click)
        with patch.object(ft.Control, "update", lambda _control: None):
            multiselect.control.on_open(None)
        self.assertTrue(multiselect.control.data["open"])
        with patch.object(ft.Control, "update", lambda _control: None):
            multiselect.control.on_close(None)
        self.assertFalse(multiselect.control.data["open"])

    def test_filter_checkbox_and_dropdown_use_canonical_semantics(self):
        checked = filter_checkbox(LIGHT_TOKENS, value=True, label="Active")
        self.assertEqual(24, checked.width)
        self.assertEqual(24, checked.height)
        self.assertEqual("#000000", checked.fill_color[ft.ControlState.SELECTED])
        selected: list[str] = []
        dropdown = single_select(
            LIGHT_TOKENS,
            value="recent",
            options=(SelectOption("recent", "Recently updated"), SelectOption("name", "Project name")),
            width=176,
            on_select=selected.append,
            role="projects-sort",
        )
        self.assertIsInstance(dropdown, ft.Dropdown)
        self.assertEqual("single", dropdown.data["selection_mode"])
        dropdown.value = "name"
        dropdown.on_select(SimpleNamespace(control=dropdown))
        self.assertEqual(["name"], selected)

    def test_project_stage_timeline_expands_small_plans_and_scrolls_large_plans(self):
        small = stage_progress_timeline(
            (
                StageTimelineItem("Discovery", "completed", "Completed", 1.0),
                StageTimelineItem("Design", "current", "60%", 0.6),
                StageTimelineItem("Delivery", "future", "Not started", 0.0),
            ),
            LIGHT_TOKENS,
        )
        self.assertFalse(small.data["scrollable"])
        self.assertIsNone(small.scroll)
        self.assertTrue(all(step.expand for step in _role(small, "project-stage-timeline-step")))

        large = stage_progress_timeline(
            tuple(StageTimelineItem(f"Stage {index}", "future", "Not started") for index in range(6)),
            LIGHT_TOKENS,
        )
        self.assertTrue(large.data["scrollable"])
        self.assertEqual(ft.ScrollMode.AUTO, large.scroll)
        self.assertTrue(all(step.width == 168 for step in _role(large, "project-stage-timeline-step")))

    def test_recent_project_activity_component_maps_real_event_kinds(self):
        activity = recent_project_activity(
            (
                ProjectActivityItem("Reviewed notes", "2h ago", ProjectActivityKind.REVIEW),
                ProjectActivityItem("Created task", "3h ago", ProjectActivityKind.TASK),
                ProjectActivityItem("Linked plan", "1d ago", ProjectActivityKind.RELATION),
            ),
            LIGHT_TOKENS,
            title="Recent updates",
            empty_message="No activity",
            open_label="Open activity",
        )
        rows = _role(activity, "project-activity-row")
        self.assertEqual(["review", "task", "relation"], [row.data["kind"] for row in rows])
        self.assertTrue(activity.data["filled"])


if __name__ == "__main__":
    unittest.main()

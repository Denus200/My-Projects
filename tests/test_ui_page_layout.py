from __future__ import annotations

import unittest

import flet as ft

from overlord.ui.components.layout import page_container, page_header, workspace_page
from overlord.ui.design_system.tokens import LIGHT_TOKENS


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control: ft.Control, role: str) -> list[ft.Control]:
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class SharedPageLayoutTests(unittest.TestCase):
    def test_title_only_header_collapses_subtitle_and_keeps_profile_right(self):
        header = page_header("Tasks", LIGHT_TOKENS)
        self.assertEqual(51, header.height)
        self.assertEqual(["Tasks"], [item.value for item in _role(header, "page-header-title")])
        self.assertEqual([], _role(header, "page-header-subtitle"))
        copy = _role(header, "page-header-copy")[0]
        self.assertFalse(copy.data["has_subtitle"])
        self.assertEqual(1, len(copy.controls))
        self.assertEqual(1, len(_role(header, "user-menu-trigger")))
        self.assertTrue(header.controls[0].expand)

    def test_title_and_subtitle_header_share_the_same_profile_structure(self):
        header = page_header("Good morning, Denys", LIGHT_TOKENS, subtitle="You have 3 tasks today")
        self.assertEqual(51, header.height)
        self.assertEqual("You have 3 tasks today", _role(header, "page-header-subtitle")[0].value)
        self.assertTrue(_role(header, "page-header-copy")[0].data["has_subtitle"])
        profile = _role(header, "user-menu-trigger")[0]
        self.assertEqual("Denys", profile.data["display_name"])
        self.assertEqual((76, 40), (profile.width, profile.height))
        self.assertEqual(20, profile.border_radius)
        self.assertEqual("#FFFFFF", profile.bgcolor)
        avatar = next(item for item in _walk(profile) if isinstance(item, ft.CircleAvatar))
        self.assertEqual(16, avatar.radius)
        avatar_holder = profile.content.controls[0]
        self.assertEqual((4, 4, 32, 32), (
            avatar_holder.left,
            avatar_holder.top,
            avatar_holder.width,
            avatar_holder.height,
        ))

    def test_page_container_owns_one_scroll_surface_and_exact_outer_padding(self):
        control = page_container(
            "Projects",
            [ft.Text("Body")],
            LIGHT_TOKENS,
            subtitle="Browse projects",
            page_id="projects",
        )
        self.assertIsInstance(control, ft.ListView)
        self.assertIs(control.scroll, ft.ScrollMode.AUTO)
        padding_layer = _role(control, "global-page-padding-layer")[0]
        self.assertEqual((24, 24, 16, 16), (
            padding_layer.padding.left,
            padding_layer.padding.right,
            padding_layer.padding.top,
            padding_layer.padding.bottom,
        ))
        self.assertEqual(0, control.padding)
        self.assertEqual(0, control.spacing)
        self.assertEqual("global-page", control.data["layout"])
        self.assertEqual("projects", control.data["page"])
        self.assertEqual(1, len(_role(control, "page-header")))
        self.assertEqual(1, len(_role(control, "page-content")))

    def test_workspace_page_gives_remaining_space_to_view_host_without_outer_scroll(self):
        header = ft.Text("Header")
        toolbar = ft.Text("Toolbar")
        view_host = ft.Container()

        control = workspace_page(
            header,
            toolbar,
            view_host,
            LIGHT_TOKENS,
            page_id="tasks",
        )

        self.assertIsInstance(control, ft.Container)
        self.assertTrue(control.expand)
        self.assertEqual((24, 24, 16, 16), (
            control.padding.left,
            control.padding.right,
            control.padding.top,
            control.padding.bottom,
        ))
        self.assertEqual("workspace-page", control.data["layout"])
        self.assertEqual("view-host", control.data["scroll_owner"])
        content = _role(control, "workspace-page-content")[0]
        self.assertTrue(content.expand)
        self.assertEqual([header, toolbar, view_host], content.controls)
        self.assertFalse(header.expand)
        self.assertFalse(toolbar.expand)
        self.assertTrue(view_host.expand)


if __name__ == "__main__":
    unittest.main()

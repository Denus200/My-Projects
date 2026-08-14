import unittest
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.ui.app import show_recovery
from overlord.ui.design_system.tokens import DARK_TOKENS, LIGHT_TOKENS
from overlord.ui.recovery import build_recovery_view


def _texts(control: ft.Control) -> list[ft.Text]:
    values: list[ft.Text] = []
    if isinstance(control, ft.Text):
        values.append(control)
    content = getattr(control, "content", None)
    if content is not None:
        values.extend(_texts(content))
    for child in getattr(control, "controls", ()) or ():
        values.extend(_texts(child))
    return values


class _Page:
    def __init__(self) -> None:
        self.title = None
        self.bgcolor = None
        self.theme = None
        self.dark_theme = None
        self.controls: list[ft.Control] = []

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)


class RecoveryViewTests(unittest.TestCase):
    def test_recovery_view_constructs_with_light_and_dark_tokens(self):
        expected = [
            "Overlord could not open safely",
            "Normal write actions are disabled. The database was not automatically recreated or restored.",
            "Error ID: error-123",
            "Database: C:\\Overlord\\overlord.db",
            "Category: Database lock error",
            "Error type: OperationalError",
            "Review data/backups and docs/architecture/DATABASE_RECOVERY.md before restoring anything.",
        ]

        for tokens in (LIGHT_TOKENS, DARK_TOKENS):
            with self.subTest(theme=tokens.app_background):
                view = build_recovery_view(
                    tokens,
                    error_id="error-123",
                    database_path="C:\\Overlord\\overlord.db",
                    category="Database lock error",
                    error_type="OperationalError",
                )
                self.assertIsInstance(view, ft.Container)
                self.assertEqual(tokens.surface_card, view.bgcolor)
                self.assertEqual(tokens.radius_card, view.border_radius)
                self.assertEqual(8, len(view.content.controls))
                self.assertEqual("icons/lucide/triangle-alert.svg", view.content.controls[0].src)
                text_controls = _texts(view)
                self.assertEqual(expected, [control.value for control in text_controls])
                self.assertTrue(text_controls[3].selectable)

    def test_show_recovery_keeps_classification_and_sanitization(self):
        cases = (
            (RuntimeError("schema private detail"), "Migration or schema error"),
            (RuntimeError("database malformed private detail"), "Database integrity error"),
            (RuntimeError("database busy private detail"), "Database lock error"),
            (PermissionError("private detail"), "Database permission error"),
            (RuntimeError("private detail"), "Unexpected startup error"),
        )

        with (
            patch("overlord.ui.app.uuid.uuid4") as uuid4,
            patch("overlord.ui.app.logging.getLogger") as get_logger,
        ):
            uuid4.return_value.hex = "1234567890abcdef"
            for error, category in cases:
                with self.subTest(category=category):
                    page = _Page()
                    show_recovery(page, error, Path("C:/Overlord/overlord.db"))
                    visible = [control.value for control in _texts(page.controls[0])]
                    self.assertEqual("Overlord — Recovery", page.title)
                    self.assertEqual(LIGHT_TOKENS.app_background, page.bgcolor)
                    self.assertIn("Error ID: 1234567890ab", visible)
                    self.assertIn(f"Category: {category}", visible)
                    self.assertIn(f"Error type: {error.__class__.__name__}", visible)
                    self.assertNotIn(str(error), visible)

            self.assertEqual(len(cases), get_logger.return_value.exception.call_count)


if __name__ == "__main__":
    unittest.main()

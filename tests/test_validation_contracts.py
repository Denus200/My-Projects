from __future__ import annotations

import unittest
from datetime import date, datetime, time

from overlord.modules.projects.domain import Project, ProjectStatus, require_project_title
from overlord.modules.settings.application import UpdateSettings
from overlord.modules.tasks.domain import require_task_title, validate_estimate, validate_schedule
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.task_form_values import (
    datetime_value,
    deadline_display,
    deadline_value,
    display_date,
    flexible_date_value,
    project_id,
    project_options,
    strict_date_value,
    time_value,
)


class ValidationContractTests(unittest.TestCase):
    def assert_field_error(self, callable_, field: str, code: str, message: str):
        with self.assertRaises(FieldValidationError) as captured:
            callable_()
        error = captured.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(field, error.field)
        self.assertEqual(code, error.code)
        self.assertEqual(message, str(error))

    def test_domain_validation_keeps_messages_and_adds_stable_metadata(self):
        cases = (
            (lambda: require_task_title("  "), "title", "required", "Task title is required."),
            (
                lambda: validate_estimate(0),
                "estimate",
                "positive",
                "Estimate must be a positive number of minutes.",
            ),
            (
                lambda: validate_schedule(None, time(9), None, None, None),
                "start_time",
                "requires_start_date",
                "A start time requires a start date.",
            ),
            (
                lambda: validate_schedule(date(2026, 8, 14), None, date(2026, 8, 13), None, None),
                "end_date",
                "before_start",
                "The end date cannot be before the start date.",
            ),
            (
                lambda: require_project_title(""),
                "title",
                "required",
                "Project title is required.",
            ),
        )
        for callable_, field, code, message in cases:
            with self.subTest(field=field, code=code, message=message):
                self.assert_field_error(callable_, field, code, message)

    def test_settings_validation_keeps_value_error_contract_and_field_metadata(self):
        command = UpdateSettings(lambda **_kwargs: self.fail("Invalid settings must not open a unit of work."))
        cases = (
            ({"locale": "de"}, "locale", "unsupported", "Language must be English or Russian."),
            ({"theme_mode": "sepia"}, "theme_mode", "unsupported", "Theme mode must be System, Light, or Dark."),
            (
                {"default_cycle_length": 0},
                "default_cycle_length",
                "range",
                "Default cycle length must be between 1 and 52 weeks.",
            ),
        )
        for changes, field, code, message in cases:
            with self.subTest(changes=changes):
                self.assert_field_error(lambda: command.execute(**changes), field, code, message)

    def test_task_form_codecs_preserve_all_accepted_date_and_time_formats(self):
        expected = date(2026, 8, 13)
        self.assertEqual(expected, strict_date_value("2026-08-13"))
        for value in ("13082026", "13.08.2026", "13/08/2026", "13-08-2026", "2026-08-13"):
            with self.subTest(value=value):
                self.assertEqual(expected, flexible_date_value(value))
        self.assertEqual(time(14, 30), time_value("14:30"))
        self.assertEqual(datetime(2026, 8, 13, 14, 30), datetime_value("2026-08-13 14:30"))
        self.assertEqual(datetime(2026, 8, 13, 14, 30), deadline_value("13.08.2026 14:30"))
        self.assertEqual(datetime(2026, 8, 13, 23, 59, 59, 999999), deadline_value("13.08.2026"))
        self.assertEqual("13.08.2026", display_date(expected))
        self.assertEqual("13.08.2026 14:30", deadline_display(datetime(2026, 8, 13, 14, 30)))

    def test_task_form_codec_failures_keep_messages_and_identify_the_source_field(self):
        cases = (
            (
                lambda: strict_date_value("13.08.2026", field="start_date"),
                "start_date",
                "date_format",
                "Date must use YYYY-MM-DD.",
            ),
            (
                lambda: flexible_date_value("invalid", field="scheduled_date"),
                "scheduled_date",
                "human_date_format",
                "Date must use DD.MM.YYYY.",
            ),
            (
                lambda: time_value("invalid", field="start_time"),
                "start_time",
                "time_format",
                "Time must use HH:MM.",
            ),
            (
                lambda: datetime_value("invalid", field="deadline"),
                "deadline",
                "datetime_format",
                "Deadline must use YYYY-MM-DD HH:MM.",
            ),
        )
        for callable_, field, code, message in cases:
            with self.subTest(field=field, code=code):
                self.assert_field_error(callable_, field, code, message)

    def test_project_codecs_preserve_none_sentinel_and_option_order(self):
        project = Project(
            7,
            "Project",
            ProjectStatus.ACTIVE,
            datetime(2026, 8, 13),
            datetime(2026, 8, 13),
        )
        options = project_options((project,))
        self.assertEqual(("none", "7"), tuple(option.key for option in options))
        self.assertIsNone(project_id(None))
        self.assertIsNone(project_id("none"))
        self.assertEqual(7, project_id("7"))


if __name__ == "__main__":
    unittest.main()

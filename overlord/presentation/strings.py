from __future__ import annotations


ENGLISH_STRINGS = {
    "dashboard.title": "Dashboard",
    "dashboard.plan_day": "Plan the day",
    "dashboard.today.title": "Today’s Tasks",
    "dashboard.today.capacity": "3 Primary · 4 Secondary",
    "dashboard.today.empty.title": "Nothing is planned for today.",
    "dashboard.today.empty.description": "Choose existing Tasks and decide what deserves your attention.",
    "dashboard.primary": "Primary",
    "dashboard.secondary": "Secondary",
    "dashboard.weekly.title": "Weekly Progress",
    "dashboard.cycle.title": "Current Cycle",
    "dashboard.attention.title": "Needs Attention",
    "dashboard.actual_time": "Actual time: {value}",
    "planning.title": "Daily Planning",
    "planning.subtitle": "Choose existing Tasks and shape a realistic day.",
    "planning.date": "Plan date",
    "planning.load_date": "Load date",
    "planning.find_tasks": "Find Tasks",
    "planning.search": "Search Tasks",
    "planning.source": "Source",
    "planning.project": "Project",
    "planning.all_sources": "All available",
    "planning.current_week": "Current week",
    "planning.overdue": "Overdue",
    "planning.active_cycle": "Active Cycle",
    "planning.primary": "Primary {count}/3",
    "planning.secondary": "Secondary {count}/4",
    "planning.assign_primary": "Assign Primary",
    "planning.assign_secondary": "Assign Secondary",
    "planning.move_up": "Move up",
    "planning.move_down": "Move down",
    "planning.remove": "Remove",
    "planning.save": "Save plan",
    "planning.cancel": "Cancel",
    "planning.no_candidates": "No Tasks match these filters.",
    "planning.empty_group": "No Tasks assigned yet.",
}


def ui_text(key: str, **values: object) -> str:
    template = ENGLISH_STRINGS[key]
    return template.format(**values) if values else template

from __future__ import annotations

import sqlite3
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from time import perf_counter

from overlord.bootstrap import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT, bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.cycles.domain import CycleStatus, WeeklyOutcomeStatus
from overlord.modules.projects.domain import ProjectPlanStatus, ProjectStageStatus, ProjectStatus
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment


DEMO_DATABASE_PATH = REPOSITORY_ROOT / "data" / "demo" / "overlord_demo.db"
DEMO_SEED_VERSION = 6


@dataclass(frozen=True, slots=True)
class DemoSeedSummary:
    database_path: Path
    project_count: int
    task_count: int
    scheduled_today_count: int
    cycle_title: str
    seed_action: str = "reused"
    completed_at: datetime | None = None
    elapsed_ms: float = 0.0


def _safe_demo_target(database_path: str | Path) -> Path:
    target = Path(database_path).resolve()
    if target == DEFAULT_DATABASE_PATH.resolve():
        raise ValueError("Demo seeding cannot target the production database.")
    return target


def _remove_demo_files(database_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{database_path}{suffix}")
        if candidate.exists():
            candidate.unlink()
    manifest = _seed_manifest_path(database_path)
    if manifest.exists():
        manifest.unlink()
    workspace_root = database_path.parent / "project-workspaces"
    if workspace_root.exists():
        shutil.rmtree(workspace_root)


def _seed_manifest_path(database_path: Path) -> Path:
    return Path(f"{database_path}.seed.json")


def _write_seed_manifest(database_path: Path, selected_day: date, completed_at: datetime) -> None:
    manifest = {
        "seed_version": DEMO_SEED_VERSION,
        "seed_date": selected_day.isoformat(),
        "semantic_fingerprint": demo_seed_fingerprint(database_path),
        "completed_at": completed_at.isoformat(timespec="milliseconds"),
    }
    _seed_manifest_path(database_path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _reusable_seed_summary(database_path: Path, selected_day: date) -> DemoSeedSummary | None:
    if not database_path.exists():
        return None
    started = perf_counter()
    manifest_path = _seed_manifest_path(database_path)
    try:
        summary = demo_seed_summary(database_path, selected_day)
        fingerprint = demo_seed_fingerprint(database_path)
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            valid = (
                manifest.get("seed_version") == DEMO_SEED_VERSION
                and manifest.get("seed_date") == selected_day.isoformat()
                and manifest.get("semantic_fingerprint") == fingerprint
            )
        else:
            valid = (
                summary.project_count == 7
                and summary.task_count == 22
                and summary.scheduled_today_count == 7
                and summary.cycle_title == "Career Launch — Cycle 2"
            )
            if valid:
                adopted_at = datetime.now()
                _write_seed_manifest(database_path, selected_day, adopted_at)
                manifest = {"completed_at": adopted_at.isoformat(timespec="milliseconds")}
        if not valid:
            return None
        if not manifest.get("completed_at"):
            adopted_at = datetime.now()
            _write_seed_manifest(database_path, selected_day, adopted_at)
            manifest["completed_at"] = adopted_at.isoformat(timespec="milliseconds")
        completed_at = datetime.fromisoformat(manifest["completed_at"])
        return DemoSeedSummary(
            summary.database_path,
            summary.project_count,
            summary.task_count,
            summary.scheduled_today_count,
            summary.cycle_title,
            "reused",
            completed_at,
            (perf_counter() - started) * 1000,
        )
    except (OSError, ValueError, KeyError, IndexError, sqlite3.DatabaseError, json.JSONDecodeError):
        return None


def seed_demo_database(
    database_path: str | Path = DEMO_DATABASE_PATH,
    *,
    today: date | None = None,
    reset: bool = True,
) -> DemoSeedSummary:
    started = perf_counter()
    target = _safe_demo_target(database_path)
    selected_day = today or date.today()
    target.parent.mkdir(parents=True, exist_ok=True)
    if reset:
        _remove_demo_files(target)
    elif target.exists():
        reusable = _reusable_seed_summary(target, selected_day)
        if reusable is not None:
            return reusable
        _remove_demo_files(target)

    services = bootstrap(target).services
    projects = {}
    project_specs = (
        ("Portfolio Refresh", "Evidence-backed case studies and portfolio polish.", "Case-study production", "#FAE9BD", True),
        ("Confident English", "Practice clear spoken explanations for interviews.", "Weekly speaking practice", "#D6F2E7", False),
        ("Overlord", "Build a calmer personal execution system.", "Foundation UX redesign", "#FFC7D2", True),
        ("Home", "Small recurring household responsibilities.", "Weekly reset", "#CCEFF3", False),
        ("Health Admin", "Collect appointments and health paperwork without forcing a false plan.", "Not started", "#E1D6F7", False),
        ("Website Launch", "A completed outcome retained for progress and history review.", "Released", "#D6F2E7", False),
        ("Old Job Search", "An archived context kept available without competing for attention.", "Archived", "#F1ECEF", False),
    )
    for title, description, stage, color, favorite in project_specs:
        project = services.projects.create_project.execute(title, description, color=color, favorite=favorite)
        projects[title] = services.projects.update_project.execute(project.id, stage_label=stage)
    projects["Website Launch"] = services.projects.update_project.execute(
        projects["Website Launch"].id,
        status=ProjectStatus.COMPLETED,
    )
    projects["Old Job Search"] = services.projects.update_project.execute(
        projects["Old Job Search"].id,
        status=ProjectStatus.ARCHIVED,
    )

    overlord_plan = services.projects.create_plan.execute(projects["Overlord"].id, "Foundation UX Improvements")
    overlord_stages = [
        services.projects.create_stage.execute(projects["Overlord"].id, overlord_plan.id, title)
        for title in ("Collect feedback", "Prioritize issues", "Design updates", "Validation")
    ]
    services.projects.change_stage_status.execute(overlord_stages[0].id, ProjectStageStatus.COMPLETED)
    services.projects.change_stage_status.execute(overlord_stages[1].id, ProjectStageStatus.COMPLETED)
    services.projects.change_stage_status.execute(overlord_stages[2].id, ProjectStageStatus.IN_PROGRESS)
    portfolio_plan = services.projects.create_plan.execute(projects["Portfolio Refresh"].id, "Portfolio Evidence Refresh")
    portfolio_stages = [
        services.projects.create_stage.execute(projects["Portfolio Refresh"].id, portfolio_plan.id, title)
        for title in ("Evidence review", "Publish case studies")
    ]
    services.projects.change_stage_status.execute(portfolio_stages[0].id, ProjectStageStatus.IN_PROGRESS)
    home_plan = services.projects.create_plan.execute(projects["Home"].id, "Home Reset")
    completed_plan = services.projects.create_plan.execute(projects["Website Launch"].id, "Website Launch Plan")
    services.projects.change_plan_status.execute(completed_plan.id, ProjectPlanStatus.COMPLETED)
    archived_plan = services.projects.create_plan.execute(projects["Old Job Search"].id, "Job Search Plan")
    services.projects.change_plan_status.execute(archived_plan.id, ProjectPlanStatus.ARCHIVED)
    services.projects.create_note.execute(
        projects["Overlord"].id,
        "Testing summary",
        "# Testing Summary\n\n## Session Overview\n\n- Reviewed onboarding flows\n- Captured usability findings\n- Prioritized the next design updates",
    )
    demo_file_source = target.parent / "project-file-sample.txt"
    demo_file_source.write_text("Deterministic local Project file used for native visual QA.\n", encoding="utf-8")
    try:
        services.projects.add_file.execute(projects["Overlord"].id, demo_file_source)
    finally:
        demo_file_source.unlink(missing_ok=True)

    week_start = selected_day - timedelta(days=selected_day.weekday())
    cycle_start = week_start - timedelta(weeks=2)
    cycle = services.cycles.create_cycle.execute(
        "Career Launch — Cycle 2",
        "Begin systematic applications with a finished CV, LinkedIn profile, and portfolio.",
        cycle_start,
        12,
    )
    services.cycles.change_status.execute(cycle.id, CycleStatus.ACTIVE)
    services.cycles.connect_project.execute(cycle.id, projects["Portfolio Refresh"].id)
    services.cycles.connect_project.execute(cycle.id, projects["Confident English"].id)
    portfolio_milestone = services.cycles.connect_milestone.execute(
        cycle.id,
        projects["Portfolio Refresh"].id,
        "Case study approved",
        "The Viora case study is accurate, readable, and approved for publication.",
    )
    english_milestone = services.cycles.connect_milestone.execute(
        cycle.id,
        projects["Confident English"].id,
        "Complete five speaking sessions",
        "Five project explanations are recorded and reviewed.",
    )

    weekly_titles = (
        "Finish CV structure",
        "Complete LinkedIn foundation",
        "Complete the first application package",
        "Publish the Viora case study",
        "Prepare interview stories",
        "Start systematic applications",
        "Review application quality",
        "Strengthen portfolio evidence",
        "Practice live interview answers",
        "Expand the target company list",
        "Follow up on active applications",
        "Close the Cycle and choose the next focus",
    )
    for week_number, title in enumerate(weekly_titles, start=1):
        if week_number == 12:
            continue
        status = WeeklyOutcomeStatus.PLANNED
        if week_number in {1, 2}:
            status = WeeklyOutcomeStatus.ACHIEVED
        elif week_number == 3:
            status = WeeklyOutcomeStatus.PARTIAL
        services.cycles.set_weekly_outcome.execute(
            cycle.id,
            week_number,
            title,
            f"Week {week_number} outcome is reviewed against its stated result.",
            status,
        )

    services.cycles.create_cycle.execute(
        "Personal Systems - Next Cycle",
        "Choose the next focused execution period after the current Cycle closes.",
        cycle.end_date + timedelta(days=1),
        12,
    )
    completed_cycle = services.cycles.create_cycle.execute(
        "Foundation Reset - Cycle 1",
        "Establish a stable weekly planning rhythm and a usable personal execution foundation.",
        cycle_start - timedelta(weeks=12),
        12,
    )
    services.cycles.connect_project.execute(completed_cycle.id, projects["Home"].id)
    for week_number, title in enumerate(
        (
            "Capture the current commitments",
            "Define the first weekly planning rhythm",
            "Complete the initial Foundation review",
        ),
        start=1,
    ):
        services.cycles.set_weekly_outcome.execute(
            completed_cycle.id,
            week_number,
            title,
            f"The result for historical week {week_number} is recorded and reviewed.",
            WeeklyOutcomeStatus.ACHIEVED if week_number < 3 else WeeklyOutcomeStatus.PARTIAL,
        )
    services.cycles.change_status.execute(completed_cycle.id, CycleStatus.COMPLETED)
    archived_cycle = services.cycles.create_cycle.execute(
        "Archived Planning Experiment",
        "Preserve an earlier planning experiment without keeping it active.",
        cycle_start - timedelta(weeks=24),
        8,
    )
    services.cycles.change_status.execute(archived_cycle.id, CycleStatus.ARCHIVED)

    created_tasks = []

    def create_task(
        project_title: str,
        title: str,
        planned_date: date,
        *,
        description: str = "",
        definition_of_done: str | None = None,
        next_action: str | None = None,
        importance: bool | None = None,
        urgency: bool | None = None,
        estimate: int | None = None,
        lifecycle: TaskLifecycle = TaskLifecycle.PLANNED,
        connect_to_cycle: bool = False,
    ):
        task = services.tasks.create_task.execute(
            projects[project_title].id,
            title,
            description=description,
            schedule_start_date=planned_date,
            definition_of_done=definition_of_done,
            next_action=next_action,
            importance=importance,
            urgency=urgency,
            estimate_minutes=estimate,
        )
        if lifecycle is TaskLifecycle.IN_PROGRESS:
            task = services.tasks.change_lifecycle.execute(task.id, lifecycle, "Demo task started")
        elif lifecycle is TaskLifecycle.COMPLETED:
            task = services.tasks.complete_task.execute(task.id)
        if connect_to_cycle:
            services.cycles.connect_task.execute(cycle.id, task.id)
        created_tasks.append(task)
        return task

    primary_one = create_task(
        "Portfolio Refresh",
        "Finalize Viora evidence section",
        selected_day,
        description="Add the verified conversion metric and source note.",
        definition_of_done="Evidence, metric source, and conclusion are complete and ready for review.",
        next_action="Insert the verified conversion metric and source note.",
        importance=True,
        urgency=False,
        estimate=45,
        lifecycle=TaskLifecycle.IN_PROGRESS,
        connect_to_cycle=True,
    )
    services.tasks.update_task.execute(
        primary_one.id,
        project_links=(
            TaskProjectAssignment(projects["Portfolio Refresh"].id, portfolio_stages[0].id),
            TaskProjectAssignment(projects["Overlord"].id, overlord_stages[2].id),
            TaskProjectAssignment(projects["Confident English"].id),
            TaskProjectAssignment(projects["Home"].id),
        ),
    )
    services.tasks.open_blocker.execute(
        primary_one.id,
        BlockerType.DEPENDENCY,
        "Waiting for confirmation of the final Viora conversion metric.",
    )
    create_task(
        "Confident English",
        "Record English project explanation",
        selected_day,
        description="Record one uninterrupted five-minute explanation.",
        definition_of_done="A five-minute explanation is recorded and one improvement note is captured.",
        next_action="Open the Viora case study and record the first uninterrupted take.",
        importance=True,
        urgency=False,
        estimate=25,
        connect_to_cycle=True,
    )
    create_task(
        "Overlord",
        "Review Overlord Dashboard",
        selected_day,
        description="Check hierarchy, density, and the three-day task board.",
        definition_of_done="Populated and empty Dashboard states are reviewed at the supported widths.",
        next_action="Check hierarchy, density, and the date-driven task list.",
        importance=True,
        urgency=True,
        estimate=30,
    )

    reference_task = create_task("Overlord", "Save Dashboard references", selected_day, next_action="Save the approved Bento and task-row references.", estimate=10)
    services.tasks.update_task.execute(
        reference_task.id,
        project_links=(TaskProjectAssignment(projects["Overlord"].id, overlord_stages[0].id),),
    )
    create_task("Portfolio Refresh", "Reply to a recruiter", selected_day, next_action="Confirm availability for a short call.", urgency=True, estimate=15)
    create_task("Portfolio Refresh", "Update LinkedIn headline", selected_day, next_action="Draft one outcome-focused headline.", importance=True, estimate=15, connect_to_cycle=True)
    create_task("Home", "Replace cat litter", selected_day, definition_of_done="Litter is replaced and the area is cleaned.", estimate=10, lifecycle=TaskLifecycle.COMPLETED)

    standalone = services.tasks.create_task.execute(
        None,
        "Buy replacement light bulbs",
        next_action="Check the kitchen fixture size before ordering.",
        importance=True,
        urgency=True,
    )
    created_tasks.append(standalone)

    carried = create_task(
        "Portfolio Refresh",
        "Prepare portfolio case-study summary",
        week_start - timedelta(weeks=2),
        definition_of_done="A concise summary names the problem, action, and evidence.",
        next_action="Reduce the draft to three evidence-backed paragraphs.",
        estimate=35,
    )
    services.tasks.update_task.execute(carried.id, schedule_start_date=selected_day - timedelta(days=1))

    stale = create_task(
        "Confident English",
        "Draft interview introduction",
        week_start - timedelta(weeks=1),
        definition_of_done="The introduction is concise, specific, and ready to rehearse.",
        next_action="Rewrite the opening with one concrete achievement.",
        importance=True,
        estimate=30,
        lifecycle=TaskLifecycle.IN_PROGRESS,
        connect_to_cycle=True,
    )
    no_next_action = create_task(
        "Overlord",
        "Review application tracking checklist",
        selected_day - timedelta(days=1),
        definition_of_done="The checklist has one clear owner and completion criterion per step.",
        importance=True,
        lifecycle=TaskLifecycle.IN_PROGRESS,
    )
    services.tasks.update_task.execute(
        no_next_action.id,
        project_links=(TaskProjectAssignment(projects["Overlord"].id, overlord_stages[1].id),),
    )

    weekly_pattern = {
        0: (2, 2),
        1: (3, 1),
        2: (2, 0),
        3: (2, 1),
        4: (2, 0),
        5: (1, 0),
        6: (1, 0),
    }
    for day_offset, (planned_count, completed_count) in weekly_pattern.items():
        planned_day = week_start + timedelta(days=day_offset)
        if planned_day == selected_day:
            continue
        for number in range(1, planned_count + 1):
            create_task(
                "Overlord",
                f"{planned_day.strftime('%A')} planning sample {number}",
                planned_day,
                definition_of_done="The sample work item is reviewed for weekly progress.",
                next_action="Complete the next visible step.",
                estimate=15,
                lifecycle=TaskLifecycle.COMPLETED if number <= completed_count else TaskLifecycle.PLANNED,
            )

    connection = sqlite3.connect(target)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "UPDATE milestones SET status='in_progress' WHERE id IN (?, ?)",
            (portfolio_milestone.id, english_milestone.id),
        )
        connection.execute(
            """
            INSERT INTO milestones (project_id,title,definition_of_done,status,position)
            VALUES (?,?,?,?,1)
            """,
            (
                projects["Overlord"].id,
                "Dashboard task flow approved",
                "The date-driven Dashboard flow is approved after populated and empty-state review.",
                "in_progress",
            ),
        )
        stale_timestamp = datetime.combine(selected_day - timedelta(days=10), time(9, 0)).isoformat(sep=" ")
        connection.execute("UPDATE tasks SET updated_at=? WHERE id=?", (stale_timestamp, stale.id))
        connection.execute(
            "UPDATE tasks SET updated_at=? WHERE id=?",
            (datetime.combine(selected_day, time(10, 0)).isoformat(sep=" "), no_next_action.id),
        )
        connection.commit()
    finally:
        connection.close()

    summary = demo_seed_summary(target, selected_day)
    completed_at = datetime.now()
    _write_seed_manifest(target, selected_day, completed_at)
    return DemoSeedSummary(
        summary.database_path,
        summary.project_count,
        summary.task_count,
        summary.scheduled_today_count,
        summary.cycle_title,
        "reset",
        completed_at,
        (perf_counter() - started) * 1000,
    )


def ensure_demo_database(database_path: str | Path = DEMO_DATABASE_PATH) -> DemoSeedSummary:
    return seed_demo_database(database_path, reset=False)


def demo_seed_summary(
    database_path: str | Path = DEMO_DATABASE_PATH,
    day: date | None = None,
) -> DemoSeedSummary:
    target = _safe_demo_target(database_path)
    selected_day = day or date.today()
    connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
    try:
        project_count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        scheduled_today_count = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE schedule_start_date <= ? AND COALESCE(schedule_end_date,schedule_start_date) >= ?",
            (selected_day.isoformat(), selected_day.isoformat()),
        ).fetchone()[0]
        cycle_title = connection.execute("SELECT title FROM cycles WHERE status='active'").fetchone()[0]
    finally:
        connection.close()
    return DemoSeedSummary(target, project_count, task_count, scheduled_today_count, cycle_title)


def demo_seed_fingerprint(database_path: str | Path = DEMO_DATABASE_PATH) -> str:
    """Hash stable demo semantics while excluding intentionally volatile timestamps."""
    target = _safe_demo_target(database_path)
    queries = (
        ("projects", "SELECT id,title,status,description,stage_label,color,favorite FROM projects ORDER BY id"),
        (
            "tasks",
            """SELECT id,project_id,title,lifecycle_status,definition_of_done,next_action,
                      importance,urgency,planned_minutes,schedule_start_date,schedule_start_time,
                      schedule_end_date,schedule_end_time,deadline_at
               FROM tasks ORDER BY id""",
        ),
        (
            "task_plans",
            """SELECT id,task_id,planned_date,planned_week_start,today_group,position,
                      supersedes_plan_id,CASE WHEN ended_at IS NULL THEN 0 ELSE 1 END
               FROM task_plans ORDER BY id""",
        ),
        ("cycles", "SELECT id,title,main_outcome,start_date,length_weeks,end_date,status FROM cycles ORDER BY id"),
        (
            "milestones",
            "SELECT id,project_id,title,definition_of_done,status,target_date,position FROM milestones ORDER BY id",
        ),
        (
            "weekly_outcomes",
            "SELECT id,cycle_id,week_number,title,definition_of_done,status FROM weekly_outcomes ORDER BY id",
        ),
        ("cycle_projects", "SELECT cycle_id,project_id,position FROM cycle_projects ORDER BY cycle_id,project_id"),
        ("project_plans", "SELECT id,project_id,title,status FROM project_plans ORDER BY id"),
        ("project_stages", "SELECT id,project_plan_id,project_id,title,status,position,start_date,end_date FROM project_stages ORDER BY id"),
        ("task_project_links", "SELECT task_id,project_id,stage_id,position FROM task_project_links ORDER BY task_id,position"),
        ("project_notes", "SELECT id,project_id,title,relative_path FROM project_notes ORDER BY id"),
        ("project_files", "SELECT id,project_id,display_name,relative_path,size_bytes FROM project_files ORDER BY id"),
        ("cycle_tasks", "SELECT cycle_id,task_id,CASE WHEN disconnected_at IS NULL THEN 0 ELSE 1 END FROM cycle_tasks ORDER BY cycle_id,task_id"),
        ("cycle_milestones", "SELECT cycle_id,milestone_id,position FROM cycle_milestones ORDER BY cycle_id,milestone_id"),
        ("blockers", "SELECT id,task_id,type,description,resolution,CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END FROM blockers ORDER BY id"),
    )
    connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
    try:
        payload = {
            name: [list(row) for row in connection.execute(sql).fetchall()]
            for name, sql in queries
        }
    finally:
        connection.close()
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()

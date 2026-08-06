from datetime import date

from core.statuses import TaskStatus, is_valid_task_status
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.task_repository import TaskRepository


class TodayService:
    def __init__(self, tasks: TaskRepository, projects: ProjectRepository):
        self.tasks = tasks
        self.projects = projects

    def get_today_tasks(self):
        return self.tasks.list_for_date(date.today(), limit=3)

    def create_task(
        self,
        project_id: int,
        title: str,
        scheduled_date: date,
        description: str = "",
        planned_minutes: int | None = None,
    ):
        if self.projects.get_by_id(project_id) is None:
            raise ValueError("Task must belong to an existing project.")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title is required.")
        return self.tasks.create(
            project_id=project_id,
            title=clean_title,
            scheduled_date=scheduled_date,
            description=description.strip(),
            planned_minutes=planned_minutes,
            status=TaskStatus.PLANNED.value,
        )

    def update_task_state(self, task_id: int, status: str, comment: str = ""):
        if not is_valid_task_status(status):
            raise ValueError(f"Unknown task status: {status}")
        return self.tasks.update_state(task_id, status, comment.strip())

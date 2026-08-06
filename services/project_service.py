from storage.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, projects: ProjectRepository):
        self.projects = projects

    def create_project(self, title: str, description: str = ""):
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Project title is required.")
        return self.projects.create(clean_title, description.strip())

    def list_active_projects(self):
        return self.projects.list_by_status("active")

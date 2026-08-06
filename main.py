import flet as ft

from services.project_service import ProjectService
from services.today_service import TodayService
from storage.database import connect_database, initialize_database
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.task_repository import TaskRepository
from ui.components.sidebar import create_sidebar
from ui.style.theme import AppStyle
from ui.views.home import home_view


def main(page: ft.Page):
    connection = connect_database()
    initialize_database(connection)
    project_repository = ProjectRepository(connection)
    task_repository = TaskRepository(connection)
    project_service = ProjectService(project_repository)
    today_service = TodayService(task_repository, project_repository)

    page.title = "Overlord"
    page.bgcolor = AppStyle.BG_MAIN
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    content_area = ft.Container(expand=True)

    def navigate(view_name):
        content_area.content = None

        if view_name == "home":
            content_area.content = home_view(page, today_service, project_service)

        page.update()

    sidebar = create_sidebar(navigate)

    page.add(
        ft.Row(
            controls=[sidebar, content_area],
            expand=True,
            spacing=0,
        )
    )

    navigate("home")


if __name__ == "__main__":
    ft.app(main)

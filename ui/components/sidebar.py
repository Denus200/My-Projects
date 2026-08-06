import flet as ft

from ui.style.theme import AppStyle


def create_sidebar(navigate_to):
    return ft.Container(
        width=250,
        bgcolor=AppStyle.BG_SIDEBAR,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text("Overlord", size=24, weight="bold", color=AppStyle.PRIMARY),
                ft.Divider(color=AppStyle.TEXT_MUTED, height=30),
                ft.TextButton(
                    "Today",
                    icon=ft.Icons.TODAY,
                    icon_color=AppStyle.PRIMARY,
                    on_click=lambda _: navigate_to("home"),
                ),
                ft.TextButton(
                    "File tools",
                    icon=ft.Icons.FOLDER,
                    icon_color=AppStyle.TEXT_MUTED,
                    disabled=True,
                ),
                ft.TextButton(
                    "Settings",
                    icon=ft.Icons.SETTINGS,
                    icon_color=AppStyle.TEXT_MUTED,
                    disabled=True,
                ),
            ]
        ),
    )

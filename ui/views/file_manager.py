# ui/views/file_manager.py
import flet as ft
from ui.style.theme import AppStyle

def file_manager_view(page: ft.Page, folder_picker: ft.FilePicker): # Получаем picker из main.py
    # --- 1. ВЫБОР ПУТИ ---
    path_field = ft.TextField(
        label="Шлях до робочої папки (вставте або оберіть)", 
        expand=True, 
        bgcolor=AppStyle.BG_SIDEBAR,
        border_color=AppStyle.PRIMARY
    )

    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.path:
            path_field.value = e.path
            page.update()

    # Привязываем результат к picker'у
    folder_picker.on_result = on_dialog_result

    # --- ФИКС 2: Асинхронный вызов диалогового окна ---
    async def open_folder_dialog(e):
        await folder_picker.get_directory_path()

    browse_btn = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        icon_color=AppStyle.PRIMARY,
        icon_size=30,
        tooltip="Обрати папку",
        on_click=open_folder_dialog # Вызываем асинхронную функцию
    )
    
    path_row = ft.Row([path_field, browse_btn])

    # --- 2. ПОЛЯ ВВОДА ---
    num_from = ft.TextField(label="Від (напр. 20)", width=120, bgcolor=AppStyle.BG_SIDEBAR)
    num_to = ft.TextField(label="До (напр. 29)", width=120, bgcolor=AppStyle.BG_SIDEBAR)
    
    subfolder_name = ft.TextField(label="Вкладена папка (опціонально)", expand=True, bgcolor=AppStyle.BG_SIDEBAR)
    suffix_name = ft.TextField(label="Суфікс (напр. _Done)", expand=True, bgcolor=AppStyle.BG_SIDEBAR)

    # --- 3. ЗОНА ПРЕДПРОСМОТРА ---
    preview_text = ft.Text("Тут з'явиться список дій після натискання 'Попередній перегляд'", color=AppStyle.TEXT_MUTED)
    preview_container = ft.Container(
        content=ft.Column([preview_text], scroll=ft.ScrollMode.AUTO),
        height=150,
        expand=True,
        bgcolor=AppStyle.BG_SIDEBAR,
        border_radius=AppStyle.RADIUS,
        padding=15
    )

    # --- 4. КНОПКИ ДЕЙСТВИЙ ---
    def generate_preview(e):
        preview_text.value = f"Готуємо прев'ю для папки:\n{path_field.value}\nДіапазон: {num_from.value} - {num_to.value}"
        preview_text.color = AppStyle.PRIMARY
        execute_btn.disabled = False
        page.update()

    # Используем новые кнопки ft.Button (вместо старых ElevatedButton)
    preview_btn = ft.Button("Попередній перегляд", icon=ft.Icons.VISIBILITY, on_click=generate_preview)
    execute_btn = ft.Button("ВИКОНАТИ", icon=ft.Icons.PLAY_ARROW, color="white", bgcolor="red600", disabled=True)

    # --- 5. ВКЛАДКИ (TabBar) ---
    tabs = ft.Tabs(
        selected_index=0,
        length=3,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Створення", icon=ft.Icons.CREATE_NEW_FOLDER),
                        ft.Tab(label="Перейменування", icon=ft.Icons.EDIT),
                        ft.Tab(label="Видалення", icon=ft.Icons.DELETE_FOREVER),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        # Экран 1
                        ft.Container(
                            padding=20,
                            content=ft.Column([
                                ft.Row([num_from, num_to]),
                                subfolder_name,
                            ])
                        ),
                        # Экран 2
                        ft.Container(
                            padding=20,
                            content=ft.Column([
                                ft.Row([num_from, num_to]),
                                suffix_name,
                            ])
                        ),
                        # Экран 3
                        ft.Container(
                            padding=20,
                            content=ft.Column([
                                ft.Row([num_from, num_to]),
                                ft.Text("Обережно! Будуть видалені папки в цьому діапазоні.", color="red400")
                            ])
                        ),
                    ]
                )
            ]
        )
    )

    return ft.Container(
        padding=40,
        expand=True,
        content=ft.Column(
            [
                ft.Text("Управління файлами", size=AppStyle.TITLE_SIZE, color=AppStyle.PRIMARY, weight="bold"),
                ft.Text("Автоматизація рутини з папками", color=AppStyle.TEXT_MAIN),
                ft.Divider(color="transparent", height=10),
                path_row,
                ft.Divider(color="transparent", height=10),
                ft.Container(content=tabs, height=250),
                ft.Divider(color=AppStyle.TEXT_MUTED, height=30),
                ft.Text("Попередній перегляд:", weight="bold", color=AppStyle.TEXT_MAIN),
                preview_container,
                ft.Row([preview_btn, execute_btn], alignment=ft.MainAxisAlignment.END)
            ]
        )
    )
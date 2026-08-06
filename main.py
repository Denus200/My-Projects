import flet as ft
import os
from pathlib import Path

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.presentation.app import OverlordApp, show_recovery


def main(page: ft.Page) -> None:
    database_path = Path(os.environ.get("OVERLORD_DB_PATH", DEFAULT_DATABASE_PATH)).resolve()
    try:
        result = bootstrap(database_path)
        OverlordApp(page, result.services).mount()
    except Exception as error:
        show_recovery(page, error, database_path)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")

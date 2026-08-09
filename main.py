import flet as ft
import logging
import os
import sys
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import DEMO_DATABASE_PATH, DemoSeedSummary, ensure_demo_database
from overlord.ui.app import OverlordApp, show_recovery


REPOSITORY_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = REPOSITORY_ROOT / "assets"
DEMO_ARGUMENT = "--demo"
WEB_ARGUMENT = "--web"
PORT_ARGUMENT = "--port"
WEB_RETIRED_MESSAGE = (
    "Overlord web mode has been retired. Run the desktop application with "
    "'python main.py' or 'python main.py --demo'."
)
_startup_lock = threading.Lock()
_startup_seed: DemoSeedSummary | None = None


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    mode: str
    database_path: Path
    development: bool


def demo_requested(arguments: list[str] | None = None, environment: dict[str, str] | None = None) -> bool:
    args = sys.argv[1:] if arguments is None else arguments
    values = os.environ if environment is None else environment
    return DEMO_ARGUMENT in args or values.get("OVERLORD_DEMO", "").strip().lower() in {"1", "true", "yes", "on"}


def startup_database_path(
    arguments: list[str] | None = None,
    environment: dict[str, str] | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    if demo_requested(arguments, values):
        return DEMO_DATABASE_PATH.resolve()
    return Path(values.get("OVERLORD_DB_PATH", DEFAULT_DATABASE_PATH)).resolve()


def development_requested(environment: dict[str, str] | None = None) -> bool:
    values = os.environ if environment is None else environment
    explicit = values.get("OVERLORD_DEVELOPMENT")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return values.get("OVERLORD_ENV", "development").strip().lower() != "production"


def desktop_runtime_arguments(arguments: list[str]) -> list[str]:
    if any(
        argument in {WEB_ARGUMENT, PORT_ARGUMENT} or argument.startswith(f"{PORT_ARGUMENT}=")
        for argument in arguments
    ):
        raise ValueError(WEB_RETIRED_MESSAGE)
    return [argument for argument in arguments if argument != DEMO_ARGUMENT]


def runtime_configuration(
    arguments: list[str] | None = None,
    environment: dict[str, str] | None = None,
) -> RuntimeConfiguration:
    values = os.environ if environment is None else environment
    is_demo = demo_requested(arguments, values)
    return RuntimeConfiguration(
        "demo" if is_demo else "production",
        startup_database_path(arguments, values),
        development_requested(values),
    )


STARTUP_RUNTIME = runtime_configuration()
STARTUP_DATABASE_PATH = STARTUP_RUNTIME.database_path


def prepare_startup(runtime: RuntimeConfiguration = STARTUP_RUNTIME) -> DemoSeedSummary | None:
    global _startup_seed
    if runtime.mode != "demo":
        return None
    with _startup_lock:
        if _startup_seed is None or _startup_seed.database_path != runtime.database_path:
            _startup_seed = ensure_demo_database(runtime.database_path)
            logging.getLogger("overlord.runtime").info(
                "demo_seed_complete database=%s action=%s seed_completed_at=%s seed_elapsed_ms=%.2f",
                runtime.database_path,
                _startup_seed.seed_action,
                _startup_seed.completed_at.isoformat(timespec="milliseconds") if _startup_seed.completed_at else "unknown",
                _startup_seed.elapsed_ms,
            )
            return _startup_seed
        return replace(_startup_seed, seed_action="reused", elapsed_ms=0.0)


def main(page: ft.Page) -> None:
    runtime = STARTUP_RUNTIME
    database_path = runtime.database_path
    try:
        seed = prepare_startup(runtime)
        result = bootstrap(database_path)
        logging.getLogger("overlord.runtime").info(
            "runtime_start mode=%s application_type=%s database=%s demo_seed=%s seed_completed_at=%s seed_elapsed_ms=%.2f development=%s",
            runtime.mode,
            "desktop",
            database_path,
            seed.seed_action if seed else "not_applicable",
            seed.completed_at.isoformat(timespec="milliseconds") if seed and seed.completed_at else "not_applicable",
            seed.elapsed_ms if seed else 0.0,
            runtime.development,
        )
        OverlordApp(page, result.services, development=runtime.development).mount()
    except Exception as error:
        show_recovery(page, error, database_path)


if __name__ == "__main__":
    launch_arguments = sys.argv[1:]
    try:
        flet_arguments = desktop_runtime_arguments(launch_arguments)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from None
    if STARTUP_RUNTIME.mode == "demo":
        prepare_startup(STARTUP_RUNTIME)
    sys.argv = [sys.argv[0], *flet_arguments]
    ft.run(main, assets_dir=str(ASSETS_DIR))

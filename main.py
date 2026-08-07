import flet as ft
import logging
import os
import sys
import tempfile
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import DEMO_DATABASE_PATH, DemoSeedSummary, ensure_demo_database
from overlord.presentation.app import OverlordApp, show_recovery


REPOSITORY_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = REPOSITORY_ROOT / "assets"
WEB_TEMP_DIR = REPOSITORY_ROOT / "data" / "runtime-tmp"
DEMO_ARGUMENT = "--demo"
WEB_ARGUMENT = "--web"
PORT_ARGUMENT = "--port"
DEFAULT_WEB_PORT = 8550
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


def web_requested(arguments: list[str] | None = None) -> bool:
    args = sys.argv[1:] if arguments is None else arguments
    return WEB_ARGUMENT in args


def web_port(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    raw_port: str | None = None
    for index, argument in enumerate(args):
        if argument == PORT_ARGUMENT and index + 1 < len(args):
            raw_port = args[index + 1]
            break
        if argument.startswith(f"{PORT_ARGUMENT}="):
            raw_port = argument.partition("=")[2]
            break
    if raw_port is None:
        return DEFAULT_WEB_PORT
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("Web port must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ValueError("Web port must be between 1 and 65535.")
    return port


def _runtime_arguments(arguments: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument in {DEMO_ARGUMENT, WEB_ARGUMENT}:
            continue
        if argument == PORT_ARGUMENT:
            skip_next = True
            continue
        if argument.startswith(f"{PORT_ARGUMENT}="):
            continue
        cleaned.append(argument)
    return cleaned


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
        application_type = "web" if bool(getattr(page, "web", False)) else "desktop"
        logging.getLogger("overlord.runtime").info(
            "runtime_start mode=%s application_type=%s database=%s demo_seed=%s seed_completed_at=%s seed_elapsed_ms=%.2f development=%s",
            runtime.mode,
            application_type,
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
    launch_web = web_requested(launch_arguments)
    launch_port = web_port(launch_arguments)
    if STARTUP_RUNTIME.mode == "demo":
        prepare_startup(STARTUP_RUNTIME)
    sys.argv = [sys.argv[0], *_runtime_arguments(launch_arguments)]
    if launch_web:
        # Force Flet's server transport without asking it to open Chrome. This
        # avoids the Flet CLI import deadlock seen with Python 3.14 on Windows
        # and keeps browser selection under the user's control.
        os.environ["FLET_FORCE_WEB_SERVER"] = "1"
        WEB_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        os.environ["TEMP"] = str(WEB_TEMP_DIR)
        os.environ["TMP"] = str(WEB_TEMP_DIR)
        tempfile.tempdir = str(WEB_TEMP_DIR)
        ft.run(main, view=None, host="127.0.0.1", port=launch_port, assets_dir=str(ASSETS_DIR))
    else:
        ft.run(main, assets_dir=str(ASSETS_DIR))

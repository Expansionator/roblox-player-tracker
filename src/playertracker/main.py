# main.py

"""
Entry point for PlayerTracker.

Initializes the application and launches the interactive CLI for tracking
and displaying Roblox player presence statuses in real time. Supports
managing tracked players by User ID and nickname.

Windows only.
"""

from __future__ import annotations

import ctypes
import platform
from typing import NoReturn, cast

from playertracker import __app_name__, __version__
from playertracker.app import App
from playertracker.cli.output import log, stop
from playertracker.core.config import DEFAULT_CONFIG, ConfigMap
from playertracker.core.service import PlayerTracker
from playertracker.core.session import try_acquire_lock
from playertracker.persistence.paths import CONFIG_PATH, ensure_app_directories
from playertracker.persistence.storage import fetch_json, write_json
from playertracker.shared.messages import AppError, SysError
from playertracker.utils.hardware import get_hardware_info
from playertracker.utils.logger import (
    get_lazy_logger,
    setup_global_exception_handler,
)
from playertracker.utils.sanitizer import sanitize_with_template

_LOGGER = get_lazy_logger(__name__)


def _load_config() -> ConfigMap | NoReturn:
    """
    Load config from disk, creating a default if none exists.

    Reads the config file at `CONFIG_PATH`. If the file is missing,
    writes `DEFAULT_CONFIG` to disk and uses it as a fallback.

    Sanitizes the loaded config against `DEFAULT_CONFIG` to fill
    any missing or invalid keys.
    """

    fetch_result = fetch_json(CONFIG_PATH)
    if not fetch_result.success:
        write_result = write_json(CONFIG_PATH, DEFAULT_CONFIG)
        if not write_result.success:
            stop(write_result.error, is_error=True)

    config = fetch_result.payload[0] if fetch_result.success else DEFAULT_CONFIG
    config = sanitize_with_template(config, DEFAULT_CONFIG)  # type: ignore[assignment]

    return cast(ConfigMap, config)


def main() -> None:

    if platform.system() != "Windows":
        stop(SysError.UNSUPPORTED_OPERATING_SYSTEM, is_error=True)

    # Set the console window title to the app name
    ctypes.windll.kernel32.SetConsoleTitleW(__app_name__)

    setup_global_exception_handler(_LOGGER)

    # Prevent multiple instances from running simultaneously
    lock_handle = try_acquire_lock()
    if lock_handle is None:
        stop(AppError.INSTANCE_ALREADY_RUNNING, is_error=True)

    log(f"Welcome to {__app_name__} v{__version__}. Starting up..", new_line="after")

    # Logs, config, and data files are written throughout the session.
    # Directories must exist before any I/O begins
    init_result = ensure_app_directories()
    if not init_result.success:
        stop(init_result.error, is_error=True)

    hw_info = get_hardware_info()

    _LOGGER.info(f"Application started: {__app_name__}")
    _LOGGER.info(f"Versions: App={__version__} | Python={platform.python_version()}")
    _LOGGER.info(f"Hardware information - {hw_info}")

    config = _load_config()

    _LOGGER.info("Initialization complete. Running app.py.")

    App(PlayerTracker(config)).run()


if __name__ == "__main__":
    main()

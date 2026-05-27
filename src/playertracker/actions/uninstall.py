# uninstall.py

"""
Provides the action implementation for uninstalling the application and
removing all associated local data from the file system.
"""

from __future__ import annotations

import atexit
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final, NoReturn, override

import psutil

from playertracker import __app_name__
from playertracker.actions.base import BaseAction
from playertracker.cli.output import log, stop
from playertracker.cli.prompt import ask_for_selection
from playertracker.persistence.paths import BASE_PATH, LOG_PATH, ROOT_PATH
from playertracker.persistence.storage import get_clean_path
from playertracker.shared.messages import AppError, DirectoryError, FileError
from playertracker.shared.typedefs import Result
from playertracker.utils.logger import close_all_loggers, get_lazy_logger

_CURRENT_EXE: Final[Path] = Path(sys.executable).resolve()
_CURRENT_PID: Final[int] = os.getpid()

# 2 seconds balances CPU efficiency with a responsive uninstallation experience
_DELAY_BETWEEN_CHECKS: Final[int] = 2

# Single quotes escaped for PowerShell compatibility
# e.g. C:\John Doe's Apps\app.exe -> C:\John Doe''s Apps\app.exe
_CURRENT_EXE_PS: Final[str] = str(_CURRENT_EXE).replace("'", "''")

# Loops until this process dies, then deletes the executable
_DELETE_CMD: Final[tuple[str, ...]] = (
    "powershell",
    "-WindowStyle",
    "Hidden",
    "-Command",
    f"while (Get-Process -Id {_CURRENT_PID} -ErrorAction SilentlyContinue) "
    f"{{ Start-Sleep -Seconds {_DELAY_BETWEEN_CHECKS} }}; "
    f"Remove-Item -Force '{_CURRENT_EXE_PS}'",
)

_LOGGER = get_lazy_logger(__name__)


def _make_writable_and_retry(
    func: Callable[[str], None] | None, path: str, exc: BaseException | None = None
) -> None:
    """
    Removes the read-only attribute from a path and retries a failed operation.
    Intended for use as an `onexc` callback with `shutil.rmtree`.

    When a deletion fails due to a permission error, this function grants write access
    to the affected path before re-invoking the originally failing callable.
    """

    # Force write permissions on Windows to bypass Access Denied errors
    os.chmod(path, stat.S_IWRITE)
    if func is not None:
        func(path)


def _find_locking_process(path: Path) -> Result:
    """
    Searches for a running process that has an open handle on a given path.

    Iterates over all active system processes and inspects their open file
    handles to determine whether any process is currently locking a file
    within the provided directory path.
    """

    # Pre-fetch "open_files" to optimize performance and reduce
    # OS overhead during iteration
    for process in psutil.process_iter(["open_files"]):
        try:
            open_files: list[Any] = process.info["open_files"] or []
            for file in open_files:
                file_path = Path(file.path)

                # Skip files that aren't inside the application directory
                if not file_path.is_relative_to(path):
                    continue

                # Lock found; abort and identify the blocking process
                return Result.err(
                    FileError.in_use(
                        get_clean_path(file_path), process_name=process.name()
                    )
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # System processes or processes closed mid-iteration can be safely skipped
            continue

    return Result.ok()


class UninstallAction(BaseAction[[]]):
    """
    An action that prompts the user for confirmation and permanently removes
    all application data from the file system.

    This class orchestrates the full uninstallation sequence, including
    deleting the application's sub-directory, cleaning up the root install
    folder, and scheduling deletion of the frozen executable itself after
    the process exits.
    """

    @staticmethod
    def _delete_app_exe() -> Result:
        """
        Schedules deletion of the frozen application executable after exit.

        When running as a frozen binary, spawns a hidden PowerShell process
        that polls until the current process has exited, then forcefully
        removes the executable from disk.

        Has no effect in non-frozen environments such as a standard Python interpreter.
        """

        # Running as a "frozen" standalone executable (e.g., packaged into an .exe)
        if getattr(sys, "frozen", False):
            # Spawn the script in a new process group so it survives after the main
            # application exits. Otherwise, Windows will kill the PowerShell subprocess
            subprocess.Popen(
                _DELETE_CMD,
                shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )

        return Result.ok()

    @staticmethod
    def _delete_sub_directory(sub_dir: Path) -> Result:
        """
        Closes all loggers and recursively deletes the application sub-directory.

        All active log file handles are released before deletion to avoid
        permission conflicts on Windows.

        If removal fails, the directory is inspected for locking processes
        before falling back to an `atexit`-registered retry.
        """

        _LOGGER.info("Preparing to delete application sub directory.")

        try:
            # Release file handles on active logs
            # Otherwise, Windows will block directory deletion
            close_all_loggers()

            shutil.rmtree(sub_dir, onexc=_make_writable_and_retry)

            log(
                "The application subfolder has been [threat]deleted[/].",
                new_line="after",
                log_level="success",
            )

        except Exception as err:
            # Scan for third-party apps (like text editors) locking our files
            response = _find_locking_process(sub_dir)
            if not response.success:
                return Result.err(response.error)

            # Queue a final deletion attempt as a fallback during application shutdown
            atexit.register(_make_writable_and_retry, None, str(sub_dir))

            return Result.err(DirectoryError.delete_failure(err))

        return Result.ok()

    @staticmethod
    def _cleanup_root_directory(root_dir: Path) -> Result:
        """
        Removes the root application directory if it is empty or user-approved.

        If the root directory is empty after the sub-directory is removed,
        it is deleted silently. Otherwise, if foreign files are detected,
        the user is prompted to confirm their removal.
        """

        try:
            # If the root directory is empty, delete it silently
            if not any(root_dir.iterdir()):
                root_dir.rmdir()
                return Result.ok()

            log(
                "The application root folder contains files that don't belong "
                f"to [app]{__app_name__}[/]."
            )
            log("Do you want to delete them?", new_line="after")

            selection = ask_for_selection(["Yes", "No"], show_selected=False)
            if selection is None:
                return Result.err(AppError.INTERRUPTED)

            if selection != 1:
                return Result.ok()

            shutil.rmtree(root_dir, onexc=_make_writable_and_retry)

            log(
                "The application root folder has been [threat]deleted[/].",
                new_line="after",
                log_level="success",
            )

        except Exception as err:
            return Result.err(DirectoryError.delete_failure(err))

        return Result.ok()

    def _uninstall(self) -> None:
        """
        Executes the core uninstallation sequence.

        Resolves the root and sub-directory paths, validates that they exist,
        and delegates deletion to the appropriate static methods. Registers
        the executable deletion callback to run after the process exits.

        Terminates the application via `stop` if any step fails.
        """

        _LOGGER.info("Preparing uninstallation of application.")

        root_dir = ROOT_PATH.resolve()
        sub_dir = BASE_PATH.resolve()

        # Abort early if the paths don't exist or aren't directories
        if not sub_dir.is_dir() or not root_dir.is_dir():
            stop(DirectoryError.APP_DIR_MISSING, is_error=True)

        sub_result = self._delete_sub_directory(sub_dir)
        if not sub_result.success:
            stop(sub_result.error, is_error=True)

        root_result = self._cleanup_root_directory(root_dir)
        if not root_result.success:
            stop(root_result.error, is_error=True)

        atexit.register(self._delete_app_exe)

    @override
    def run(self) -> NoReturn:
        """
        Executes the interactive uninstallation workflow.

        Presents the user with a clear warning about permanent data loss
        and requires explicit confirmation before proceeding. Cancels and
        exits cleanly if the user declines or if input is interrupted.

        Raises:
            SystemExit: Always. Either after a successful uninstall or
                upon cancellation.
        """

        _LOGGER.info("Uninstall Action: Preparing to delete program directory.")
        _LOGGER.info("Requesting confirmation for deletion.")

        log(
            "This will [threat]permanently delete[/] all data for "
            f"[app]{__app_name__}[/], including all [warning]local application data[/] "
            f"and [warning]{LOG_PATH.name}[/].",
            log_level="danger",
        )

        log(
            "This action is [threat]irreversible[/].",
            new_line="after",
            log_level="danger",
        )

        log("Are you sure you want to continue?", new_line="after")

        confirmation = ask_for_selection(
            ["[threat]Yes, delete everything[/]", "No, cancel and exit"],
            show_selected=False,
        )

        if confirmation is None:
            stop(AppError.INTERRUPTED, is_error=True)

        if confirmation == 2:
            _LOGGER.info(
                "User requested to exit; initiating application shutdown sequence."
            )
            stop(thank_msg=True)

        _LOGGER.info("Confirmation met to delete program directory. Deleting.")

        self._uninstall()
        stop(thank_msg=True, no_log=True)

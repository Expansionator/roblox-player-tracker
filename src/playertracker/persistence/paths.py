# paths.py

"""
Critical path objects required by the application.

These paths represent essential directories and files, including
configuration files and user data storage locations. The paths are
used throughout the application to ensure consistent access to
required resources.

This module is also responsible for ensuring that required directories
exist before use. If necessary, directories are automatically created
under the system's LocalAppData directory, using a unique GUID-based
folder structure to isolate application data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from platformdirs import user_data_path

from playertracker import __app_name__
from playertracker.core.config import PROGRAM_ID
from playertracker.persistence.storage import get_clean_path
from playertracker.shared.decorators import log_lifecycle
from playertracker.shared.messages import CommonError, DirectoryError, SysError
from playertracker.shared.typedefs import Result

_LOG_NAME: Final[str] = "app.log"
_CONFIG_NAME: Final[str] = "config.json"
_USER_DATA_NAME: Final[str] = "user_data.json"
_CACHE_FOLDER_NAME: Final[str] = ".cache"

_LOCAL_APPDATA: Final[Path] = user_data_path()

ROOT_PATH: Final[Path] = _LOCAL_APPDATA / __app_name__
BASE_PATH: Final[Path] = ROOT_PATH / PROGRAM_ID

LOG_PATH: Final[Path] = BASE_PATH / _LOG_NAME
CONFIG_PATH: Final[Path] = BASE_PATH / _CONFIG_NAME
USER_DATA_PATH: Final[Path] = BASE_PATH / _USER_DATA_NAME
CACHE_FOLDER_PATH: Final[Path] = BASE_PATH / _CACHE_FOLDER_NAME


@log_lifecycle(
    start="Preparing directories for application.",
    end="Directory preparation completed successfully.",
    silent=True,
)
def ensure_app_directories() -> Result:
    """
    Creates the required directories for the application.

    Ensures that all necessary application directories exist before use.
    If any required directories are missing, they are created automatically.

    Returns:
        Result: A `Result` instance indicating whether directory creation was
            successful or failed.

    Examples:
        >>> result = ensure_app_directories()
        >>> if not result.success:
        ...     print(result.error)
    """

    clean_path = get_clean_path(BASE_PATH)
    try:
        if BASE_PATH.exists() and not BASE_PATH.is_dir():
            return Result.err(DirectoryError.is_file(clean_path))

        BASE_PATH.mkdir(parents=True, exist_ok=True)

    except PermissionError:
        return Result.err(SysError.no_permission(clean_path))
    except OSError as err:
        return Result.err(SysError.filesystem_error(err))
    except Exception as err:
        return Result.err(CommonError.unexpected(err))

    return Result.ok()

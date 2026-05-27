# storage.py

"""
Provides file I/O operations for reading, writing, and formatting JSON data safely.

This module handles disk persistence for configuration profiles and user data mapping.
It wraps standard file operations in exception-safe blocks, automatically catching
filesystem or corruption errors and routing them into structured `Result` wrappers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from playertracker.core.config import ConfigMap
from playertracker.shared.decorators import log_lifecycle
from playertracker.shared.messages import CommonError, FileError, SysError
from playertracker.shared.typedefs import Result, UserData

# The character encoding standard used for all file read and write operations.
_ENCODING: Final[str] = "utf-8"

# The number of spaces used for indentation when formatting serialized JSON output.
_DEFAULT_INDENT: Final[int] = 4

# The maximum number of trailing path components to include
# when truncating paths for logging.
_MAX_PARTS_IN_DIR: Final[int] = 3

type Data = UserData | ConfigMap


@log_lifecycle(start="Obtaining cleaned version of target path object.", silent=True)
def get_clean_path(path: Path) -> str:
    """
    Truncates a file path into a shortened format suitable for clean log outputs.

    If the provided path contains more than three directory components, it collapses
    the intermediate directories into an ellipsis to keep log outputs compact.

    Args:
        path: The absolute or relative filesystem path to format.

    Returns:
        clean_path: A string representation of the path, truncated if
            it exceeds length thresholds.

    Examples:
        >>> from pathlib import Path
        >>> get_clean_path(Path("usr/local/bin/app/config.json"))
        'bin/.../config.json'
        >>> get_clean_path(Path("app/config.json"))
        'app/config.json'
    """

    parts = path.parts
    if len(parts) > _MAX_PARTS_IN_DIR:
        return f"{parts[-_MAX_PARTS_IN_DIR]}/.../{parts[-1]}"

    return str(path)


@log_lifecycle(
    start="Attempting to load target JSON data.", end="JSON data loaded successfully."
)
def fetch_json(path: Path) -> Result[Data]:
    """
    Reads and parses a JSON file from disk into an application-safe data model.

    Args:
        path: The filesystem path pointing to the target JSON file.

    Returns:
        Result: A `Result` instance containing the parsed dictionary payload
            (UserData or ConfigMap) if successful, or a specific failure
            message detailing corruption, missing files, or permission blocks.

    Examples:
        >>> from pathlib import Path
        >>> result = fetch_json(Path("non_existent_file.json"))
        >>> result.success
        False
    """

    clean_path = get_clean_path(path)
    try:
        with path.open("r", encoding=_ENCODING) as file:
            data = json.load(file)
            return Result.ok(data)

    except FileNotFoundError:
        return Result.err(FileError.not_found(clean_path))
    except json.JSONDecodeError:
        return Result.err(FileError.corrupt(clean_path))
    except PermissionError:
        return Result.err(SysError.no_permission(clean_path))
    except Exception as err:
        return Result.err(CommonError.unexpected(err))


@log_lifecycle(
    start="Attempting to write target data sequence.",
    end="Data write sequence completed successfully.",
)
def write_json(path: Path, data: Data) -> Result:
    """
    Serializes and writes application data structures safely to disk as formatted JSON.

    Args:
        path: The filesystem path where the JSON file should be saved.
        data: The dictionary sequence payload (`UserData` or `ConfigMap`)
            to be serialized.

    Returns:
        Result: A `Result` instance indicating whether the file write sequence
            succeeded or failed due to disk constraints or OS permission errors.

    Examples:
        >>> from pathlib import Path
        >>> mock_data = {"user_ids": [123], "user_names": {}}
        >>> result = write_json(Path("output.json"), mock_data)
    """

    clean_path = get_clean_path(path)
    try:
        with path.open("w", encoding=_ENCODING) as file:
            json.dump(data, file, indent=_DEFAULT_INDENT)
            return Result.ok()

    except PermissionError:
        return Result.err(SysError.no_permission(clean_path))
    except OSError as err:
        return Result.err(SysError.filesystem_error(err))
    except Exception as err:
        return Result.err(CommonError.unexpected(err))

# messages.py

"""
Dataclass definitions that store error messages used throughout the application.

These classes represent structured error message containers for different
error types. Some messages are static constants, while others accept
arguments to generate dynamic error messages.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final

from requests import exceptions


@dataclass(frozen=True)
class CommonError:
    @staticmethod
    def unexpected(err: Exception | None = None) -> str:
        return "Something went wrong" + (
            f": {err}" if err is not None else ". Please try again."
        )


@dataclass(frozen=True)
class AppError:
    INTERRUPTED: Final[str] = "The application was closed unexpectedly."
    INSTANCE_ALREADY_RUNNING: Final[str] = "The application is already running."


@dataclass(frozen=True)
class InputError:
    REQUIRED: Final[str] = "This field cannot be empty."
    NOT_INTEGER: Final[str] = "Please enter a whole number."

    OUT_OF_BOUNDS: Final[str] = "That option doesn't exist. Please choose a valid one."


@dataclass(frozen=True)
class UserIdError:
    NO_USER_IDS_FOUND: Final[str] = "No available User IDs were found."

    INVALID_USER_IDS: Final[str] = (
        "Too many provided, or one or more User ID(s) are invalid."
    )

    USER_ID_EXISTS: Final[str] = (
        "That User ID already exists. Please try a different one."
    )

    MISSING_USER_ID: Final[str] = (
        "That User ID doesn't exist. Please try a different one."
    )

    USER_QUOTA_EXCEEDED: Final[str] = (
        "You've reached the maximum number of User IDs. Please remove one before "
        "adding a new one."
    )

    INVALID_USER_ID_FORMAT: Final[str] = (
        "No valid User ID(s) were found. Please check that your IDs are correct "
        "and try again."
    )


@dataclass(frozen=True)
class UsernameError:
    MISSING_USER_NAMES: Final[str] = "No nicknames were found."

    USER_ID_AND_NAME_MISMATCH: Final[str] = (
        "The number of nicknames must match the number of User IDs."
    )


@dataclass(frozen=True)
class SysError:
    UNSUPPORTED_OPERATING_SYSTEM: Final[str] = "This application only supports Windows."

    @staticmethod
    def filesystem_error(err: OSError) -> str:
        return f"A file system error occurred: {err}"

    @staticmethod
    def no_permission(path: str) -> str:
        return f"Permission denied. The application can't read or write to: {path}"


@dataclass(frozen=True)
class DirectoryError:
    APP_DIR_MISSING: Final[str] = "One or more required application folders are missing."

    @staticmethod
    def is_file(path: str) -> str:
        return f"Expected a folder but found a file at: {path}"

    @staticmethod
    def delete_failure(err: Exception) -> str:
        return f"Could not delete the folder: {err}"


@dataclass(frozen=True)
class FileError:
    @staticmethod
    def in_use(path: str, process_name: str) -> str:
        return (
            f"Can't access {path} because it's open in {process_name}. "
            "Please close it and try again."
        )

    @staticmethod
    def not_found(path: str) -> str:
        return f"File not found: {path}"

    @staticmethod
    def corrupt(path: str) -> str:
        return f"The file at {path} appears to be corrupted or has an invalid format."


@dataclass(frozen=True)
class DatabaseError:
    @staticmethod
    def execution_failure(err: sqlite3.DatabaseError) -> str:
        return f"Failed to save your data: {err}"

    @staticmethod
    def timeout(path: str) -> str:
        return (
            f"Could not write to {path} because the database is busy. Please try again."
        )


@dataclass(frozen=True)
class RequestError:
    REQUEST_TIMEOUT: Final[str] = (
        "The request timed out. Please check your connection and try again."
    )
    SERVER_CONNECTION_FAILED: Final[str] = (
        "Could not reach the server. Please check your connection."
    )

    @staticmethod
    def bad_response(err: exceptions.HTTPError) -> str:
        if err.response is None:
            return "A network error occurred. Please try again later."

        return (
            f"The server returned an unexpected response ({err.response.status_code}). "
            "Please try again later."
        )


@dataclass(frozen=True)
class CooldownError:
    @staticmethod
    def rate_limited(remaining: int | float) -> str:
        mins, secs = divmod(int(remaining), 60)
        mins_part = f" {mins} min and " if mins > 0 else " "

        return f"Please wait{mins_part}{secs} sec before running the application again."

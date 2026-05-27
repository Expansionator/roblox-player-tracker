# typedefs.py

"""
Central repository for application type aliases, data schemas, and execution wrappers.

This module consolidates domain-specific types to ensure consistent type hints across
the application. It defines strict layouts for player data dictionaries using `TypedDict`
and implements an immutable `Result` container to streamline structured, exception-safe
error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ReadOnly, TypedDict

from playertracker.utils.logger import get_lazy_logger

_LOGGER = get_lazy_logger(__name__)


class PresenceInfo(TypedDict):
    presence_type: ReadOnly[int]


class UserData(TypedDict):
    user_ids: UserIds
    user_names: UsernameMap


type ParsedData = dict[str, PresenceInfo]

type UserId = int
type Username = str

type UserIds = list[UserId]

type Usernames = list[Username]
type UsernameMap = dict[str, Username]

type RawUserIds = str
type RawUsernames = str


@dataclass(frozen=True, kw_only=True)
class Result[*Ts = *tuple[Any, ...]]:
    """
    An immutable container capturing the outcome of an execution sequence.

    Encapsulates functional-style error handling by packaging a boolean success
    status, an optional descriptive error string, and an arbitrary unpackable
    tuple payload of variable types (`*Ts`).

    Attributes:
        success: True if the operation completed successfully; False otherwise.
        error: A descriptive warning message if an failure occurred, otherwise None.
        payload: A strongly-typed tuple containing variable operational outputs.
    """

    success: bool = True
    error: str | None = None

    payload: tuple[*Ts] = ()  # type: ignore[assignment]

    @classmethod
    def ok[*NewTs](cls, *payload: *NewTs) -> Result[*NewTs]:
        """
        Constructs a successful `Result` instance.

        Args:
            *payload: A variable number of unpackable arguments containing the
                successful outputs of the operation.

        Returns:
            Result: A successful `Result` instance enclosing the
                unpacked payload elements.

        Examples:
            >>> result = Result.ok("User Found", 42)
            >>> result.success
            True
            >>> result.payload
            ('User Found', 42)
        """

        return cls(success=True, payload=payload, error=None)  # type: ignore[return-value]

    @classmethod
    def err(cls, msg: str | None = None) -> Result[*tuple[Any, ...]]:
        """
        Constructs a failed `Result` instance and logs an execution warning.

        Args:
            msg: An optional string message describing the failure reason.

        Returns:
            Result: A failed `Result` instance containing no payload and
                the failure message.

        Examples:
            >>> result = Result.err("Connection timed out.")
            >>> result.success
            False
            >>> result.error
            'Connection timed out.'
        """

        _LOGGER.warning(
            msg if msg is not None else "Exception intercepted during execution sequence."
        )
        return cls(success=False, payload=(), error=msg)  # type: ignore[return-value]

# session.py

"""
Ensures that only one instance of the application can be opened at a time.
This functionality is only supported on Windows operating systems.
"""

from __future__ import annotations

import ctypes
from typing import Final

from playertracker.core.config import PROGRAM_ID

# WinAPI: Object already exists
_WIN_ERROR_ALREADY_EXISTS: Final[int] = 183


def try_acquire_lock() -> int | None:
    """
    Return a mutex handle if this is the first instance, else `None`.

    Returns:
        mutex: A Windows mutex handle for the newly acquired application lock
            if no other instance is running. Otherwise `None` if the mutex
            already exists.

    Example:
        >>> lock = try_acquire_lock()
    """

    # Create a named mutex shared across processes
    k32 = ctypes.windll.kernel32
    mutex = k32.CreateMutexW(None, False, PROGRAM_ID)

    if k32.GetLastError() == _WIN_ERROR_ALREADY_EXISTS:
        k32.CloseHandle(mutex)
        return

    return mutex

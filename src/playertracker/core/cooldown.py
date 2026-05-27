# cooldown.py

"""
Enforces a cooldown period before the application can be used again.

Uses a cache to store the application's start time retrieved from an
external API endpoint. The cached timestamp is then compared against
the current time to determine whether the cooldown period has expired.
"""

from __future__ import annotations

import sqlite3
from typing import Final

from diskcache import Cache, JSONDisk

from playertracker.persistence.paths import CACHE_FOLDER_PATH
from playertracker.persistence.storage import get_clean_path
from playertracker.shared.decorators import log_lifecycle
from playertracker.shared.messages import CommonError, DatabaseError, SysError
from playertracker.shared.typedefs import Result

_ENABLED: Final[bool] = True
_COOLDOWN_PERIOD: Final[float] = 90.0

_KEY_IN_CACHE: Final[str] = "last_usage_time"


class CooldownSystem:
    """
    Manages and enforces application-wide execution cooldown periods.

    This system utilizes a localized disk cache (`diskcache.Cache`) backed by
    SQLite to store and persist the timestamp of the application's last
    successful external API request. It prevents hitting endpoints too quickly
    by calculating the delta between past execution and current system times.

    Attributes:
        enabled: A boolean flag indicating whether the cooldown checking
            mechanism is active.
        cache: The disk cache instance used to persist execution
            timestamps, or None if initialization failed or system is disabled.
    """

    def __init__(self):
        self.enabled = False
        self.cache: Cache | None = None

    @classmethod
    def setup(cls) -> Result[CooldownSystem]:
        """
        Creates a new instance of `CooldownSystem` and initializes its cache
        within the application directory.

        Returns:
            Result: A `Result` instance containing the `Cooldown` instance.

        Examples:
            >>> result = CooldownSystem.setup()
            >>> if not result.success:
            ...     return result.error
            >>> cooldown = result.payload[0]
        """

        instance = cls()
        clean_path = get_clean_path(CACHE_FOLDER_PATH)

        if not _ENABLED:
            return Result.ok(instance)

        try:
            # JSONDisk is used instead of pickle-based storage to avoid
            # pickle deserialization vulnerabilities.
            instance.cache = Cache(CACHE_FOLDER_PATH, disk=JSONDisk)

        except PermissionError:
            return Result.err(SysError.no_permission(clean_path))
        except sqlite3.DatabaseError as err:
            return Result.err(DatabaseError.execution_failure(err))
        except Exception as err:
            return Result.err(CommonError.unexpected(err))

        instance.enabled = True
        return Result.ok(instance)

    @log_lifecycle(start="Checking application reusability status post-expiry.")
    def is_expired(
        self, now: float, delay: float = _COOLDOWN_PERIOD
    ) -> tuple[bool, float | None]:
        """
        Checks whether enough time has elapsed since the application's last usage.

        This is typically used in conjunction with `update()` to enforce cooldown
        or rate-limiting behavior.

        Args:
            now: The current system time in seconds since the Unix epoch. Used to
                record when the application made an API request.

            delay: The required delay, in seconds, before the application can
                be used again.

        Returns:
            is_expired: Whether the application can be used again.

            remaining: The amount of time, in seconds, remaining
                before the application can be used again.

        Examples:
            >>> now = 1600000000.0
            >>> delay = 60.0
            >>> cooldown = CooldownSystem.setup()
            >>> is_expired, remaining = cooldown.is_expired(now, delay)
        """

        if not self.enabled or self.cache is None:
            return True, None

        last_run = self.cache.get(_KEY_IN_CACHE)
        if last_run is None:
            return True, None

        time_diff = now - last_run
        if time_diff < delay:
            remaining = delay - time_diff
            return False, remaining

        return True, None

    @log_lifecycle(start="Refreshing application expiry timer for reusability.")
    def update(self, now: float) -> Result:
        """
        Refreshes the cached timestamp that controls application execution.

        Updates the stored cache value so that the application is prevented
        from running again until the cooldown or validity period has elapsed.

        Args:
            now: The current system time in seconds since the Unix epoch. Used to record
                when the application made an API request.

        Returns:
            Result: A `Result` instance indicating whether the cache was
                successfully updated.

        Examples:
            >>> now = 1600000000.0
            >>> cooldown = CooldownSystem.setup()
            >>> result = cooldown.update(now)
        """

        if not self.enabled or self.cache is None:
            return Result.ok()

        clean_path = get_clean_path(CACHE_FOLDER_PATH)
        try:
            self.cache.set(_KEY_IN_CACHE, now)

        except TimeoutError:
            return Result.err(DatabaseError.timeout(clean_path))
        except sqlite3.DatabaseError as err:
            return Result.err(DatabaseError.execution_failure(err))
        except Exception as err:
            return Result.err(CommonError.unexpected(err))

        return Result.ok()

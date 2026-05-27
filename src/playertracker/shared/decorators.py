# decorators.py

"""
Logging and execution flow decorators for the application.

This module provides reusable decorators to log function execution to the
application log file, manage post-execution exit prompts, and enforce
successful `Result` states before proceeding.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from playertracker.cli.output import stop
from playertracker.cli.prompt import handle_exit
from playertracker.shared.typedefs import Result
from playertracker.utils.logger import get_lazy_logger

_LOGGER = get_lazy_logger(__name__)


def log_lifecycle[**P, R](
    start: str = "Function started.",
    end: str = "Function finished.",
    silent: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator factory that logs the start and end of a function to the log file.

    Args:
        start: The message to write to the log file before execution.
        end: The message to write to the log file after execution finishes.
        silent: Whether to suppress logging for this execution.

    Returns:
        A decorator function that wraps the target function with file logging.

    Examples:
        >>> @log_lifecycle(start="Fetching data...", end="Data fetched successfully.")
        ... def fetch_user_profile(user_id: int):
        ...     return {"id": user_id, "name": "Alice"}
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not silent:
                _LOGGER.info(start)

            result = func(*args, **kwargs)

            if not silent:
                _LOGGER.info(end)

            return result

        return wrapper

    return decorator


def confirm_exit[**P, R2: Result](func: Callable[P, R2]) -> Callable[P, R2]:
    """
    A decorator that triggers an exit confirmation prompt after a function runs.

    Args:
        func: The function to execute before prompting the user for exit.

    Returns:
        The wrapped function which executes the original logic followed by the
        exit handler.

    Examples:
        >>> @confirm_exit
        ... def close_session() -> Result:
        ...     return Result(success=True)
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R2:
        result = func(*args, **kwargs)
        handle_exit()

        return result

    return wrapper


def require_success[**P, R2: Result](func: Callable[P, R2]) -> Callable[P, R2]:
    """
    A decorator that stops execution if the wrapped function returns a failed Result.

    If the returned `Result` instance indicates failure (`success` is False), the
    decorator intercepts the flow, prints the error, and terminates execution.

    Args:
        func: The function returning a `Result` instance to check.

    Returns:
        The wrapped function. Returns the result normally if it is successful.

    Examples:
        >>> @require_success
        ... def load_configuration() -> Result:
        ...     # If a config file is missing, halts the program and prints the error.
        ...     return Result(success=False, error="Config missing")
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R2:
        result = func(*args, **kwargs)
        if not result.success:
            stop(result.error, is_error=True)

        return result

    return wrapper

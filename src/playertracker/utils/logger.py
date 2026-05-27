# logger.py

"""
Logging setup for PlayerTracker.

Provides a lazy logger that defers file handler creation until first use,
rotating file handlers shared across loggers writing to the same path,
and a global exception hook to capture uncaught crashes.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from types import TracebackType
from typing import Final

# Only log messages at INFO level or higher (e.g., WARNING, ERROR, CRITICAL)
_LEVEL: Final[int] = logging.INFO

# Explicitly force UTF-8 to prevent encoding crashes if the app logs emojis or
# foreign characters on Windows systems (which default to CP1252/Windows-1252)
_ENCODING: Final[str] = "utf-8"

_LOG_FORMAT: Final[str] = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
_LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

_MAX_LOG_SIZE: Final[int] = 5_000_000  # 5 MB
_MAX_BACKUPS: Final[int] = 3

_UNHANDLED_EXCEPTION: Final[str] = "Uncaught exception"

_HANDLERS = logging.handlers

_loggers_container: list[logging.Logger] = []
_handlers_container: dict[Path, _HANDLERS.RotatingFileHandler] = {}


def _get_logger(name: str, path: Path | None = None) -> logging.Logger:
    """Configures and returns a cached or new rotating file logger."""

    from playertracker.persistence.paths import LOG_PATH

    if path is None:
        path = LOG_PATH

    absolute_path = path.resolve()

    logger = logging.getLogger(name)
    logger.setLevel(_LEVEL)
    logger.propagate = False  # Prevent logs from bubbling up to console/root logger

    # This logger already has handlers configured
    if logger.handlers:
        return logger

    # Share the existing handler if another logger is writing to the same path
    if absolute_path in _handlers_container:
        logger.addHandler(_handlers_container[absolute_path])
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)
    handle = _HANDLERS.RotatingFileHandler(
        absolute_path,
        maxBytes=_MAX_LOG_SIZE,
        backupCount=_MAX_BACKUPS,
        delay=True,  # Delay creating the file until the first log is written
        encoding=_ENCODING,
    )

    handle.setLevel(_LEVEL)
    handle.setFormatter(formatter)

    _handlers_container[absolute_path] = handle

    logger.addHandler(handle)
    return logger


class LazyLogger:
    """
    A proxy wrapper that defers logger instantiation until its first use.

    Attributes:
        name: The string identifier for the underlying logger.
        logger: The underlying `logging.Logger` instance, or `None`
            if it has not yet been instantiated.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger: logging.Logger | None = None

    def __getattr__(self, item: str):
        """Instantiates the logger on first attribute access and proxies the call."""

        if self.logger is None:
            self.logger = _get_logger(self.name)
            _loggers_container.append(self.logger)

        return getattr(self.logger, item)


def get_lazy_logger(name: str) -> LazyLogger:
    """
    Factory function to initialize a `LazyLogger` instance.

    Args:
        name: The name of the logger, preferably the file name from which
            the logger is created.

    Returns:
        LazyLogger: A `LazyLogger` instance that exposes methods compatible with
            `logging.Logger`.
    """

    return LazyLogger(name)


def close_all_loggers() -> None:
    """Flushes, closes, and detaches all active handlers from tracked loggers."""

    for logger in _loggers_container:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    _handlers_container.clear()
    _loggers_container.clear()


def setup_global_exception_handler(logger: LazyLogger) -> None:
    """
    Overrides sys.excepthook to route uncaught crashes into the logger.

    Bypasses critical user-interrupt actions like `KeyboardInterrupt` and `EOFError`
    so terminal termination still behaves normally.

    Args:
        logger: The `LazyLogger` instance used to record the critical traceback payload.
    """

    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:

        if issubclass(exc_type, (KeyboardInterrupt, EOFError)):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            _UNHANDLED_EXCEPTION, exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

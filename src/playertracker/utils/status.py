# status.py

"""
CLI progress bar utilities for displaying operation status.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Final

from alive_progress import alive_bar

from playertracker.cli.output import log

_BAR_TYPE: Final[str] = "smooth"
_SPINNER_TYPE: Final[str] = "dots_waves"


@contextmanager
def create_bar(total_items: int) -> Generator[Any]:
    """
    Yields a configured progress bar context.

    Initializes an `alive_bar` with pre-defined visual styles ('smooth' and
    'dots_waves') and yields the bar control object. Automatically logs a
    final newline or status cleanup message when exiting the context.

    Args:
        total_items: The total number of steps or items the progress bar
            will track.

    Yields:
        alive_bar: The progress bar instance to increment inside the context.

    Examples:
        >>> with create_bar(10) as bar:
        ...     for i in range(10):
        ...         # do work
        ...         bar()
    """

    try:
        with alive_bar(
            total_items, bar=_BAR_TYPE, spinner=_SPINNER_TYPE, enrich_print=True
        ) as bar:  # type: ignore[assignment]
            yield bar
    finally:
        log()

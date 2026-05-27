# output.py

"""
Handles terminal text display and controlled program termination.

Provides utilities for displaying formatted text in the terminal, including
support for custom styling such as colored words, horizontal separators,
and optional spacing between messages.

Also includes functionality for stopping the program gracefully, though
termination behavior may have certain limitations depending on the execution
environment or context.
"""

from __future__ import annotations

import sys
from typing import Literal, NoReturn

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from playertracker.utils.logger import get_lazy_logger

_BAR_CHAR: str = "\u2500"  # "─"

THEME: Theme = Theme(
    {
        "prompt": "grey70",
        "symbol": "bold cyan",
        "info": "bold cyan",
        "app": "bold cyan",
        "success": "bold green",
        "error": "bold red",
        "danger": "bold red",
        "header": "bold",
        "selection": "bold",
        "threat": "bold red",
        "warning": "red",
        "content": "yellow",
        "offline": "dim white",
        "online": "bold blue",
        "playing": "bold green",
    }
)

CONSOLE: Console = Console(highlight=False, theme=THEME, color_system="truecolor")
_LOGGER = get_lazy_logger(__name__)


def _get_section_bar(msg: str) -> str:
    return _BAR_CHAR * len(msg)


def log(
    msg: str | None = None,
    new_line: Literal["before", "after"] | None = None,
    log_level: Literal["info", "success", "error", "danger"] = "info",
    draw_bar: bool = False,
) -> None:
    """
    Print a styled log message to the console.

    Supports optional spacing before or after the message, colored log
    level headers, and an optional section bar separator.

    Args:
        msg: The message to display. If `None`, only a blank line is printed.

        new_line: Controls extra spacing around the log output.

            - `"before"`: Insert a blank line before the message.
            - `"after"`: Insert an extra blank line after the message.
            - `None`: No additional spacing.

        log_level: The visual style and label used for the log header.

            Supported values:
            - `"info"`
            - `"success"`
            - `"error"`
            - `"danger"`

        draw_bar: Whether to print a decorative section bar beneath the message.

    Examples:
        >>> log("Hello [blue]World[/]!", "after")
        Hello World!
    """

    is_msg_empty = msg is None
    if is_msg_empty or new_line == "before":
        CONSOLE.print()
        if is_msg_empty:
            return

    header = Text(f"[ {log_level.upper()} ]:", style=log_level)
    suffix = "\n\n" if new_line == "after" else "\n"

    CONSOLE.print(header, msg, end=suffix if not draw_bar else "\n", soft_wrap=True)

    if draw_bar:
        section_bar = _get_section_bar(f"{header.plain} {msg}")
        CONSOLE.print(section_bar, end=suffix)

    return


def stop(
    msg: str | None = None,
    is_error: bool = False,
    thank_msg: bool = False,
    make_bef_line: bool = False,
    no_log: bool = False,
) -> NoReturn:
    """
    Terminates the program with a custom or default message.

    Supports multiple termination types, such as `error` for runtime failures
    or `info` for normal program termination without errors. The displayed
    message can be customized based on the termination context.

    Args:
        msg: The message shown before the built-in message.
        is_error: Whether to set the context to `ERROR`.
        thank_msg: Includes a thank-you message displayed after the main message.
        make_bef_line: Inserts a new line before displaying the main message.

        no_log: Whether to disable logging to log files.
            Useful when the program has been uninstalled and
            no further log files should be created.

    Raises:
        SystemExit: Always.

    Examples:
        >>> stop("Application is now stopping!", thank_msg=True)
        Application is now stopping!

        Thank you for using this application!\n
        Stopping application..

        Press Enter to exit...
    """

    level = "error" if is_error else "info"

    if not no_log:
        if is_error:
            _LOGGER.critical(
                msg
                if msg is not None
                else "Aborting execution sequence due to critical error."
            )
        else:
            _LOGGER.info("Application finished successfully.")

    if msg is not None:
        log(msg, log_level=level, new_line="before" if make_bef_line else None)

    if thank_msg:
        log("Thank you for using this application!")

    log("Stopping application..", log_level=level, new_line="after")

    try:
        CONSOLE.input("Press Enter to exit... ")
    except (KeyboardInterrupt, EOFError):
        pass

    sys.exit(1 if is_error else 0)

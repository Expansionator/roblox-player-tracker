# prompt.py

"""
Prompt utilities for collecting validated user input.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, cast

from playertracker.cli.output import CONSOLE, log, stop
from playertracker.shared.messages import AppError, InputError
from playertracker.utils.logger import get_lazy_logger

_DEFAULT_PROMPT: Final[str] = "Enter Option"

_EXIT_LIST: Final[Sequence[str]] = ["Continue", "Exit"]
_EXIT_SELECTION: Final[int] = 2

_LOGGER = get_lazy_logger(__name__)


def handle_exit() -> None:
    """
    Prompts the user to continue or quit the program.

    Raises:
        SystemExit: When the user chooses to exit the program.

    Examples:
        >>> handle_exit()
        Enter Option (1-2) > 1 (Continue)
        None

        >>> handle_exit()
        Enter Option (1-2) > 2 (Exit)
        SystemExit
    """

    selection = ask_for_selection(_EXIT_LIST, show_selected=False)
    if selection == _EXIT_SELECTION:
        stop(thank_msg=True)

    return


def ask(msg: str, is_int: bool = False) -> str | int | None:
    """
    Prompts the user for a validated response.

    Supports free-form text responses and integer-based inputs.
    String responses may include whitespace such as usernames or nicknames.

    Args:
        msg: The message displayed to the user.
        is_int: Whether the provided input must be convertible to an integer.

    Returns:
        response: The user's response as a string, or an
            integer when the input represents a numeric selection. Returns
            `None` if a valid response could not be obtained.

    Raises:
        SystemExit: Raised when input is interrupted by `KeyboardInterrupt`
            or `EOFError`.

    Examples:
        >>> name = ask("What's your name?")
        What's your name? > John Doe
        >>> name
        John Doe

        >>> age = ask("What's your age?")
        What's your age? > 18
        >>> age, type(age)
        18 <class 'int'>
    """

    _LOGGER.info("Initiating user prompt sequence.")

    while True:
        try:
            response = CONSOLE.input(f"[prompt]{msg}[/] [symbol]>[/] ").strip()
            log()

            if not response:
                log(InputError.REQUIRED, log_level="error", new_line="after")
                continue

            response = int(response) if is_int else response

        except (KeyboardInterrupt, EOFError):
            log(new_line="before")
            stop(AppError.INTERRUPTED, is_error=True, make_bef_line=True)

            return

        except ValueError:
            log(InputError.NOT_INTEGER, log_level="error", new_line="after")
            continue

        _LOGGER.info("User prompt sequence completed.")
        return response


def ask_for_selection(
    options: list[str],
    msg: str = _DEFAULT_PROMPT,
    show_selected: bool = True,
) -> int | None:
    """
    Prompts the user to select from multiple available options.

    Displays a numbered list of string-based options and expects the user
    to provide a valid integer corresponding to one of the available
    selections. The order of the provided options determines the displayed
    selection index.

    Optionally, the current selection may be displayed after the list of
    available options.

    If the provided input falls outside the valid option range, the program
    terminates execution.

    Args:
        options: A sequentially ordered list of string options presented to the user.

        msg: The prompt message displayed before the options, typically including
            context such as the valid input range (e.g., "(0-3)").

        show_selected: Whether to display the currently selected option
            after input is received.

    Returns:
        selection: The index of the user's selected option from
            the menu, or `None` if a valid selection could not be made.

    Raises:
        SystemExit: Raised when input is interrupted by `KeyboardInterrupt`
            or `EOFError`, or when the provided input is out of the valid
            option range.

    Examples:
        >>> selection = ask_for_selection(["Yes", "No"], msg="Please pick")
        Please pick (1-2) > 1
        >>> selection
        1
    """

    total_options = len(options)

    def display_options() -> None:
        for index, option in enumerate(options):
            display_num = index + 1
            is_last_option = display_num == total_options

            header = f"[[header]{display_num}[/]]:"

            log(f"{header} {option}", new_line="after" if is_last_option else None)

        return

    def is_within_range(option: int) -> bool:
        return 1 <= option <= total_options

    _LOGGER.info("Initiating multi-option selection sequence.")

    log("Select an option:")
    display_options()

    option = ask(msg + f" (1-{total_options})", is_int=True)
    option = cast(int, option)

    if not is_within_range(option):
        stop(InputError.OUT_OF_BOUNDS, is_error=True)

    if show_selected:
        value = options[option - 1]
        log(f"Selected: [selection]{value}[/]", new_line="after")

    _LOGGER.info("Multi-option selection completed.")

    return option

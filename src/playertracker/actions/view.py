# view.py

"""
Provides the action implementation for displaying tracked User IDs in the terminal.
"""

from __future__ import annotations

from typing import Final, override

from playertracker.actions.base import BaseAction
from playertracker.cli.output import log
from playertracker.core.service import UserIds, UsernameMap
from playertracker.shared.typedefs import Result, UserId
from playertracker.utils.logger import get_lazy_logger

# The maximum number of User IDs to render horizontally in a single terminal row
_MAX_USER_IDS_TO_DISPLAY: Final[int] = 5

_LOGGER = get_lazy_logger(__name__)


class ViewAction(BaseAction[[UserIds, UsernameMap]]):
    """
    An action that formats and renders tracked User IDs to the terminal.

    This class handles chunks of User IDs, maps them to their respective
    nicknames if available, and outputs them cleanly to the terminal
    in a structured grid layout.
    """

    def _display_user_ids(self, user_ids: UserIds, user_names: UsernameMap) -> None:
        """Chunks and renders the tracked User IDs with their associated nicknames."""

        def _custom_map(user_id: UserId) -> str:

            str_user_id = str(user_id)
            if str_user_id in user_names:
                return f"{str_user_id} ({user_names[str_user_id]})"

            return str_user_id

        user_id_range = range(0, len(user_ids), _MAX_USER_IDS_TO_DISPLAY)
        for index in user_id_range:
            user_ids_in_row = user_ids[index : index + _MAX_USER_IDS_TO_DISPLAY]
            content = ", ".join(map(_custom_map, user_ids_in_row))

            is_last_item = index == user_id_range[-1]

            log(f"[content]{content}[/]", new_line="after" if is_last_item else None)

        return

    @override
    def run(self, user_ids: UserIds, user_names: UsernameMap) -> Result:
        """
        Executes the workflow to display the tracked User IDs.

        This method coordinates logging headers and triggering the inner
        display loop to output user data cleanly.

        Args:
            user_ids: A collection of User IDs to display.
            user_names: A dictionary mapping string User IDs to their
                corresponding nicknames.

        Returns:
            Result: A successful `Result` instance after the User IDs
                have been formatted and rendered to the terminal.
        """

        _LOGGER.info("View Action: Preparing to display User IDs.")

        log("Displaying results..")
        log(f"User IDs ({_MAX_USER_IDS_TO_DISPLAY} per row):", new_line="after")

        self._display_user_ids(user_ids, user_names)

        _LOGGER.info("User IDs successfully rendered and finalized.")
        return Result.ok()

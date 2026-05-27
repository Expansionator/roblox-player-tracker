# modify.py

"""
Provides the action implementation for modifying tracked User IDs and nicknames.
"""

from __future__ import annotations

from typing import override

from playertracker.actions.base import BaseAction
from playertracker.cli.output import log
from playertracker.cli.prompt import ask, ask_for_selection
from playertracker.core.service import UserIds, UsernameMap
from playertracker.shared.messages import AppError
from playertracker.shared.typedefs import Result
from playertracker.utils.logger import get_lazy_logger

_LOGGER = get_lazy_logger(__name__)


class ModifyAction(BaseAction[[UserIds, UsernameMap]]):
    """
    An action that facilitates updating, adding, or removing User IDs and nicknames.

    This class presents interactive CLI choices allowing the user to select
    whether they want to manage raw tracking IDs or adjust the human-readable
    nicknames associated with those IDs.
    """

    def _modify_user_id(self, user_ids: UserIds) -> Result:
        """Prompts the user to add or remove a single User ID from tracking."""

        _LOGGER.info("User chosen to modify User ID.")
        _LOGGER.info("Initiating selection prompt sequence; awaiting user input.")

        selection = ask_for_selection(["Add", "Remove"], show_selected=False)
        if selection is None:
            return Result.err(AppError.INTERRUPTED)

        log(
            f"Which User ID would you like to {'add' if selection == 1 else 'remove'}?",
            new_line="after",
        )

        # Ensure User ID is a valid integer first
        raw_user_id = ask("Enter User ID", is_int=True)
        if not isinstance(raw_user_id, int):
            return Result.err(AppError.INTERRUPTED)

        _LOGGER.info("User selection captured successfully; processing choice.")

        # Convert User ID to string for JSON compatibility
        raw_user_id = str(raw_user_id)
        response = (
            self.tracker.add_user_id(raw_user_id, user_ids)
            if selection == 1
            else self.tracker.remove_user_id(raw_user_id, user_ids)
        )

        if not response.success:
            return Result.err(response.error)

        log("Affected User ID updated!", new_line="after", log_level="success")
        _LOGGER.info("User ID modification completed successfully.")

        return Result.ok()

    def _modify_user_name(self, user_ids: UserIds, user_names: UsernameMap) -> Result:
        """Prompts the user to assign, update, or clear nicknames for specific IDs."""

        _LOGGER.info("User chosen to modify nickname.")
        _LOGGER.info("Initiating selection prompt sequence; awaiting user input.")

        selection = ask_for_selection(["Add / Update", "Remove"], show_selected=False)
        if selection is None:
            return Result.err(AppError.INTERRUPTED)

        action = "assign/update" if selection == 1 else "remove"

        log(f"Which User ID(s) would you like to {action} nicknames for?")
        log(
            f"Separate them with commas (e.g., 10001{self.sep} 10002{self.sep} 10003).",
            new_line="after",
        )

        raw_user_ids = ask("Enter User ID(s)")
        if not isinstance(raw_user_ids, str):
            return Result.err(AppError.INTERRUPTED)

        _LOGGER.info("User selection captured successfully; processing choice.")

        if selection == 1:
            _LOGGER.info("User appending nicknames for each User ID. Awaiting input.")

            log("Enter a nickname for each User ID.")
            log(
                "Make sure they match the same order as your User IDs.",
                new_line="after",
            )
            log(
                f"Separate them with commas (e.g., John Doe{self.sep} Bob{self.sep} Tom)",
                new_line="after",
            )

            raw_user_names = ask("Enter Nickname(s)")
            if not isinstance(raw_user_names, str):
                return Result.err(AppError.INTERRUPTED)

            response = self.tracker.add_user_names(
                user_ids=user_ids,
                user_names=user_names,
                raw_user_ids=raw_user_ids,
                raw_user_names=raw_user_names,
            )
        else:
            response = self.tracker.remove_user_names(user_names, raw_user_ids)

        if not response.success:
            return Result.err(response.error)

        log("Affected nickname(s) updated!", new_line="after", log_level="success")
        _LOGGER.info("Nicknames modification completed successfully.")

        return Result.ok()

    @override
    def run(self, user_ids: UserIds, user_names: UsernameMap) -> Result:
        """
        Executes the interactive modification workflow.

        Routes the user through selection menus to either alter the tracked
        User ID collections or update their mapped nicknames.

        Args:
            user_ids: A collection of currently tracked User IDs.
            user_names: A dictionary mapping string User IDs to their
                corresponding nicknames.

        Returns:
            Result: A `Result` instance indicating whether the modifications
                were successfully applied.
        """

        _LOGGER.info(
            "Modify Action: Preparing to request to edit User IDs and/or Nicknames."
        )

        selection = ask_for_selection(["User ID", "Nickname"])
        if selection is None:
            return Result.err(AppError.INTERRUPTED)

        response = (
            self._modify_user_id(user_ids)
            if selection == 1
            else self._modify_user_name(user_ids, user_names)
        )

        if not response.success:
            return Result.err(response.error)

        _LOGGER.info("User ID and/or Nicknames modification completed successfully.")

        return Result.ok()

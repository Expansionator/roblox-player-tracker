# create.py

"""
Provides the action implementation for creating and tracking new user data.
"""

from __future__ import annotations

from typing import override

from playertracker.actions.base import BaseAction
from playertracker.cli.output import log
from playertracker.cli.prompt import ask
from playertracker.shared.messages import AppError
from playertracker.shared.typedefs import Result
from playertracker.utils.logger import get_lazy_logger

_LOGGER = get_lazy_logger(__name__)


class CreateAction(BaseAction[[]]):
    """
    An action that prompts the user for User IDs, validates them,
    and initiates tracking.

    This class handles the interactive CLI workflow for collecting User IDs
    from the terminal, validating the input format, and committing them to
    the core service layer for processing and persistent storage.
    """

    @override
    def run(self) -> Result:
        """
        Executes the interactive workflow to collect and track new user IDs.

        This method prompts the user via the terminal, processes
        the comma-separated string of IDs, and passes them to the internal
        `PlayerTracker` instance for loading and persistence.

        Returns:
            Result: A `Result` instance indicating whether the user data
                was successfully saved.
        """

        _LOGGER.info("Create Action: Requesting user input and loading user data.")

        log("Enter the User ID(s) you'd like to track.")
        log(
            f"Separate them with commas (e.g., 10001{self.sep} 10002{self.sep} 10003).",
            new_line="after",
        )

        raw_user_ids = ask("Enter User ID(s)")
        if not isinstance(raw_user_ids, str):
            return Result.err(AppError.INTERRUPTED)

        response = self.tracker.load_user_data(raw_user_ids)
        if not response.success:
            return Result.err(response.error)

        log("User ID(s) saved!", new_line="after", log_level="success")
        _LOGGER.info("User input captured; user data loaded successfully.")

        return Result.ok()

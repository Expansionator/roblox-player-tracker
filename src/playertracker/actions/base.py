# base.py

"""
Provides the foundational abstract base class for all actions that are
processed and requested before fully loading and calling the API request.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from playertracker.core.service import PlayerTracker
from playertracker.shared.typedefs import Result


class BaseAction[**P](ABC):
    """
    The abstract base class that all actions must inherit from.

    This class standardizes how actions access the `PlayerTracker`
    instance, its configuration, and defines the execution contract via the
    `run` method.

    Attributes:
        tracker: The `PlayerTracker` instance.
        config: The configuration from `PlayerTracker` instance.
        sep: The string separator used for splitting User IDs (e.g., ",").
    """

    def __init__(self, tracker: PlayerTracker):
        """
        Initializes the BaseAction with a tracker instance.

        Args:
            tracker: An instance of `PlayerTracker` providing core services
                and configuration data.
        """

        self.tracker = tracker

        self.config = self.tracker.config
        self.sep = self.config["SEPARATOR"]

    @abstractmethod
    def run(self, *args: P.args, **kwargs: P.kwargs) -> Result[*tuple[Any, ...]]:
        """
        Executes the specific action logic.

        This method must be implemented by all subclasses. It accepts arbitrary
        arguments and keyword arguments.

        Args:
            *args: Positional arguments required by the action implementation.
            **kwargs: Keyword arguments required by the action implementation.

        Returns:
            Result: A `Result` instance containing a tuple of the action's
                execution output.
        """
        pass

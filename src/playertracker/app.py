# app.py

"""
Top-level application controller for PlayerTracker.

Coordinates the full runtime flow, from the initial menu selection through
user data loading, cooldown enforcement, presence fetching, and result
rendering.

Delegates discrete operations to their respective action classes
and core service layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import floor
from time import time
from typing import Any, Final, NoReturn

from playertracker import __app_name__
from playertracker.actions import (
    BaseAction,
    CreateAction,
    ModifyAction,
    UninstallAction,
    ViewAction,
)
from playertracker.cli.output import log, stop
from playertracker.cli.prompt import ask_for_selection
from playertracker.core.cooldown import CooldownSystem
from playertracker.core.service import PlayerTracker, UserIds, UsernameMap
from playertracker.persistence.paths import USER_DATA_PATH
from playertracker.persistence.storage import get_clean_path
from playertracker.shared.constants import (
    PRESENCE_TYPE_KEY,
    USER_IDS_KEY,
    USER_NAMES_KEY,
)
from playertracker.shared.decorators import confirm_exit, log_lifecycle, require_success
from playertracker.shared.messages import CommonError, CooldownError, UserIdError
from playertracker.shared.typedefs import ParsedData, Result
from playertracker.utils.logger import get_lazy_logger
from playertracker.utils.status import create_bar

# Extra spacing applied between a player's display name or
# status label and its adjacent column
_EXTRA_PADDING: Final[int] = 2

# Do not modify the order as it must strictly match the API response schema
_PRESENCE_MAP: Final[Sequence[str]] = ["Offline", "Online", "Playing"]

# Index-matched to _PRESENCE_MAP. Keys correspond to Rich
# theme styles defined in output.py
_COLOR_PRESENCE_MAP: Final[Sequence[str]] = ["offline", "online", "playing"]

_LOGGER = get_lazy_logger(__name__)

type PlayerData = dict[int, list[str]]
type DisplayNames = dict[str, str]


class App:
    """
    The top-level controller that drives the PlayerTracker runtime.

    Orchestrates the main menu, user data resolution, API interactions,
    and terminal output. All discrete operations are delegated to action
    classes via `_run_action`.

    Attributes:
        tracker: The `PlayerTracker` instance.
        config: The configuration extracted from the `PlayerTracker` instance.
    """

    def __init__(self, tracker: PlayerTracker):
        self.tracker = tracker
        self.config = self.tracker.config

    def _run_action[**P](
        self, action: type[BaseAction[P]], *args: P.args, **kwargs: P.kwargs
    ) -> Result[*tuple[Any, ...]]:
        """Instantiates the action class and runs its run method."""
        return action(self.tracker).run(*args, **kwargs)

    @require_success
    def _create(self) -> Result:
        """Delegates to `CreateAction` to prompt the user for new User IDs to track."""
        return self._run_action(CreateAction)

    @confirm_exit
    @require_success
    def _modify(self, user_ids: UserIds, user_names: UsernameMap) -> Result:
        """Delegates to `ModifyAction` to interactively update User IDs or nicknames."""
        return self._run_action(ModifyAction, user_ids, user_names)

    @confirm_exit
    @require_success
    def _view(self, user_ids: UserIds, user_names: UsernameMap) -> Result:
        """Delegates to `ViewAction` to render the User IDs in the terminal."""
        return self._run_action(ViewAction, user_ids, user_names)

    def _uninstall(self) -> NoReturn:  # type: ignore[reportReturnType]
        """Delegates to `UninstallAction` to permanently remove all application data."""
        self._run_action(UninstallAction)

    @log_lifecycle(start="Initiating cooldown cache creation and refresh sequence.")
    def _enforce_cooldown(self) -> Result:
        """
        Initializes the cooldown system and blocks execution if the
        cooldown period has not elapsed.
        """

        setup_result = CooldownSystem.setup()
        if not setup_result.success:
            return Result.err(setup_result.error)

        cooldown = setup_result.payload[0]
        now = time()

        is_expired, remaining = cooldown.is_expired(now)
        if not is_expired and remaining is not None:
            return Result.err(CooldownError.rate_limited(remaining))

        update_result = cooldown.update(now)
        if not update_result.success:
            return Result.err(update_result.error)

        return Result.ok()

    @log_lifecycle(start="Initiating API POST request to retrieve player presences.")
    def _fetch_data(self, user_ids: UserIds) -> Result[ParsedData]:
        """
        Requests player presences from an external API and returns the parsed response.
        """

        total_chunks, _ = self.tracker.get_totals(user_ids)
        with create_bar(total_chunks) as bar:
            result = self.tracker.fetch_presences(user_ids, on_progress=bar)

        if not result.success:
            return Result.err(result.error)

        return Result.ok(result.payload[0])

    @log_lifecycle(start="Initiating player presence grouping sequence by type.")
    def _group_by_presence(self, parsed_data: ParsedData) -> PlayerData:
        """Groups parsed player data by presence type into a keyed dictionary."""

        player_data: PlayerData = {p_type: [] for p_type, _ in enumerate(_PRESENCE_MAP)}
        for user_id, user_info in parsed_data.items():
            user_presence_type = user_info[PRESENCE_TYPE_KEY]

            # Only a specific set of statuses is allowed: "Offline", "Online",
            # and "Playing". If the presence type falls outside these,
            # it defaults to "Offline" or "Online" if in Roblox Studio
            if user_presence_type > len(player_data):
                # Value	| Roblox Label
                # 0	    | Offline
                # 1	    | Online
                # 2	    | InGame
                # 3	    | InStudio
                # 4	    | Invisible
                user_presence_type = 1 if user_presence_type == 3 else 0

            player_data[user_presence_type].append(user_id)

        return player_data

    @log_lifecycle(start="Preparing to parse and render player summary.")
    def _show_summary(self, player_data: PlayerData, total_user_ids: int) -> None:
        """
        Renders a presence count summary to the terminal, showing the total
        and percentage share for each status.
        """

        longest_status = max(len(s) for s in _PRESENCE_MAP)
        last_index = len(_PRESENCE_MAP) - 1

        # Iterate backwards to display the "Playing" status row at the top
        # and "Offline" at the bottom, prioritizing higher-importance statuses.
        for index, status in enumerate(_PRESENCE_MAP[::-1]):
            sub_data = player_data[last_index - index]

            padding = (longest_status + _EXTRA_PADDING) - len(status)
            col = " " * padding

            total_data = len(sub_data)
            percentage = floor((total_data / total_user_ids) * 100)

            log(
                f"{status}{col}: [header]{total_data}[/] ({percentage}%)",
                new_line="after" if index == last_index else None,
            )

        return

    @log_lifecycle(start="Initiating display name dictionary mapping sequence.")
    def _build_display_names(
        self, parsed_data: ParsedData, user_names: UsernameMap
    ) -> DisplayNames:
        """
        Maps each User ID to a display string, appending a nickname if one is available.
        """

        display_names: DisplayNames = {}
        for user_id in parsed_data.keys():
            if user_id in user_names:
                display_names[user_id] = f"{user_id} ({user_names[user_id]})"
                continue

            display_names[user_id] = user_id

        return display_names

    @log_lifecycle(start="Preparing to parse and render player information.")
    def _show_details(self, parsed_data: ParsedData, display_names: DisplayNames) -> None:
        """
        Renders each player's presence status alongside their User ID and nickname,
        or User ID alone if no nickname is set.
        """

        longest_key = max(len(k) for k in display_names.values())
        last_index = len(parsed_data) - 1

        for index, (user_id, user_info) in enumerate(parsed_data.items()):
            key = display_names[user_id]

            padding = (longest_key + _EXTRA_PADDING) - len(key)
            gap = " " * padding

            presence_type = user_info[PRESENCE_TYPE_KEY]

            presence = _PRESENCE_MAP[presence_type]
            color = _COLOR_PRESENCE_MAP[presence_type]

            log(
                f"{key}{gap}: [{color}]{presence}[/]",
                new_line="after" if index == last_index else None,
            )

        return

    def _load_menu(self) -> None:
        """
        Loads persisted user data and routes the user to continue, modify,
        or view before fetching player presences.
        """

        _LOGGER.info("Initiating user data load or creation sequence.")

        log(f"Loading data from {get_clean_path(USER_DATA_PATH)}")
        log("Loading..", new_line="after")

        result = self.tracker.load_user_data()
        if not result.success:
            stop(result.error, is_error=True)

        _LOGGER.info("User data resolution completed successfully.")
        _LOGGER.info("Requesting confirmation for 'Continue' | 'Modify' | 'View'")

        user_data = self.tracker.user_data
        if user_data is None:
            stop(CommonError.unexpected(), is_error=True)

        user_ids = user_data[USER_IDS_KEY]
        user_names = user_data[USER_NAMES_KEY]

        # user_ids may be empty if it was sanitized due to an invalid format
        # (e.g., manual tampering with the user_data JSON). This will cause downstream
        # errors since subsequent operations require valid IDs to process player presence.
        if not user_ids:
            stop(UserIdError.NO_USER_IDS_FOUND, is_error=True)

        match ask_for_selection(["Continue", "Modify", "View"]):
            case 1:
                pass
            case 2:
                self._modify(user_ids, user_names)
            case 3:
                self._view(user_ids, user_names)
            case _:
                pass

        _LOGGER.info("Request operation completed.")

    def _track(self) -> None:
        """
        Enforces cooldown, fetches player presences, and renders
        the summary and detail views.
        """

        _LOGGER.info("Running _track method sequence.")
        _LOGGER.info("Initiating total calculation and cooldown sequence.")

        user_data = self.tracker.user_data
        if user_data is None:
            stop(CommonError.unexpected(), is_error=True)

        user_ids = user_data[USER_IDS_KEY]
        user_names = user_data[USER_NAMES_KEY]

        _, total_user_ids = self.tracker.get_totals(user_ids)

        cooldown_result = self._enforce_cooldown()
        if not cooldown_result.success:
            stop(cooldown_result.error, is_error=True)

        _LOGGER.info("Cooldown metrics successfully refreshed.")
        _LOGGER.info(
            "Initiating player presence retrieval and progress rendering sequence."
        )

        log("Fetching data...")
        log("This may take a moment.", new_line="after")

        fetch_result = self._fetch_data(user_ids)
        if not fetch_result.success:
            stop(fetch_result.error, is_error=True)

        log("Data fetched successfully!", log_level="success")
        log("Displaying results...", new_line="after")

        _LOGGER.info("Presence synchronization and progress tracking finalized.")
        _LOGGER.info("Preparing to generate player summary overview.")

        parsed_data = fetch_result.payload[0]
        player_data = self._group_by_presence(parsed_data)

        log(f"Showing [header]{total_user_ids}[/] player(s).", new_line="after")
        log("Player Summary", draw_bar=True)

        self._show_summary(player_data, total_user_ids)

        _LOGGER.info("Player summary display finalized.")
        _LOGGER.info("Awaiting user confirmation to display detailed results.")

        selection = ask_for_selection(["View details", "Exit"])
        if selection == 2:
            stop(thank_msg=True)

        _LOGGER.info("Preparing to generate detailed player overview.")

        log("Player Details", draw_bar=True)

        display_names = self._build_display_names(parsed_data, user_names)
        self._show_details(parsed_data, display_names)

        _LOGGER.info("Player detailed overview rendered and finalized.")

        stop(thank_msg=True)

    def run(self) -> None:
        """
        Starts the application and drives the top-level menu flow.

        Presents the user with options to create new tracking data, load
        existing data, or uninstall the application.

        After a selection is handled, control is passed to `_track` to fetch
        and display player presence results.
        """

        _LOGGER.info(
            "Running app.py: Requesting confirmation for 'Create' | 'Load' | 'Uninstall'."
        )

        log(f"{__app_name__} is ready.", new_line="after")
        log("Track and compare the status of Roblox players in real time.")
        log(
            "Useful for checking if multiple players are in the same experience.",
            new_line="after",
        )

        log(
            "Note: Results depend on each player's privacy settings and may "
            "not always be available.",
            new_line="after",
        )

        match ask_for_selection(["Create", "Load", "Uninstall"]):
            case 1:
                self._create()
            case 2:
                self._load_menu()
            case 3:
                self._uninstall()
            case _:
                pass

        _LOGGER.info("Request operation completed.")
        _LOGGER.info("Invoking _track method sequence.")

        self._track()

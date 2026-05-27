# service.py

"""
Core service layer for PlayerTracker.

Handles user data persistence, input parsing and validation, payload
construction, and concurrent presence fetching from the Roblox presence API.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from math import ceil
from typing import Any, Final, ReadOnly, TypedDict, cast

from requests import Response, Session, exceptions

from playertracker.core.config import ConfigMap
from playertracker.persistence.paths import USER_DATA_PATH
from playertracker.persistence.storage import fetch_json, write_json
from playertracker.shared.constants import (
    PRESENCE_TYPE_KEY,
    USER_IDS_KEY,
    USER_NAMES_KEY,
)
from playertracker.shared.decorators import log_lifecycle, require_success
from playertracker.shared.messages import (
    CommonError,
    RequestError,
    UserIdError,
    UsernameError,
)
from playertracker.shared.typedefs import (
    ParsedData,
    RawUserIds,
    RawUsernames,
    Result,
    UserData,
    UserIds,
    UsernameMap,
    Usernames,
)
from playertracker.utils.logger import get_lazy_logger
from playertracker.utils.sanitizer import sanitize_with_template

# Prevents requests from hanging indefinitely
_MAX_TIMEOUT: Final[float] = 10.0

# Caps the number of concurrent threads dispatched to the presence API
_MAX_WORKERS: Final[int] = 5

_TARGET_URL: Final[str] = "https://presence.roblox.com/v1/presence/users"

# JSON keys from the Roblox API response and request body
_PRESENCE: Final[str] = "userPresences"
_USER_ID: Final[str] = "userId"
_USER_IDS: Final[str] = "userIds"
_PRESENCE_TYPE: Final[str] = "userPresenceType"

# Roblox User IDs are 64-bit integers, so values must fall within this range
_MAX_INT64: Final[int] = (2**63) - 1

# Used to sanitize loaded JSON data, filling in any missing keys with their defaults
_USER_DATA_TEMPLATE: Final[dict[str, UserIds | UsernameMap]] = {
    USER_IDS_KEY: [],
    USER_NAMES_KEY: {},
}

_LOGGER = get_lazy_logger(__name__)


class Payload(TypedDict):
    """A typed request body containing a batch of User IDs for a single API POST."""

    userIds: ReadOnly[Sequence[int]]


type Payloads = list[Payload]
type FetchResult = Result[Response]


def _cast_user_id(value: str) -> int | None:
    """
    Parses a string into a valid positive int64 User ID,
    or returns `None` if invalid.
    """

    try:
        n = int(value)
    except ValueError:
        return None

    return n if 0 < n < _MAX_INT64 else None


@log_lifecycle(start="Obtaining FetchResult from payload via POST API.")
def _fetch_presence(url: str, payload: Payload | None = None) -> FetchResult:
    """Sends a POST request to the presence API and returns the raw response."""

    try:
        with Session() as session:
            json_payload = cast(Any, payload)

            response = session.post(url, timeout=_MAX_TIMEOUT, json=json_payload)
            response.raise_for_status()  # Raises an HTTPError for 4xx/5xx status codes

    except exceptions.Timeout:
        return Result.err(RequestError.REQUEST_TIMEOUT)
    except exceptions.ConnectionError:
        return Result.err(RequestError.SERVER_CONNECTION_FAILED)
    except exceptions.HTTPError as err:
        return Result.err(RequestError.bad_response(err))
    except (exceptions.RequestException, Exception) as err:
        return Result.err(CommonError.unexpected(err))

    return Result.ok(response)


@log_lifecycle(start="Parsing Response object(s) into dict format.")
def _parse_presences(responses: list[Response]) -> ParsedData:
    """
    Extracts and merges presence data from a list of API responses into a single dict.
    """

    parsed_presences: ParsedData = {}
    for response in responses:
        try:
            data = response.json()
        except ValueError:
            continue

        if _PRESENCE not in data:
            continue

        # Response JSON body e.g.:
        # {"userPresences": [{"userId": 12345, "userPresenceType": 2}, ...]}
        #
        # Parsed into e.g.:
        # {"12345": {"presence_type": 2}, "67890": {"presence_type": 0}}
        parsed_presences.update(
            {
                str(user_info[_USER_ID]): {PRESENCE_TYPE_KEY: user_info[_PRESENCE_TYPE]}
                for user_info in data[_PRESENCE]
            }
        )

    return parsed_presences


class PlayerTracker:
    """
    The core service class responsible for managing tracked player data and
    fetching their presence information from the Roblox API.

    Handles the full lifecycle of user data. From parsing and validating raw
    input, to persisting changes to disk, to dispatching concurrent API
    requests and returning parsed presence results.

    Attributes:
        config: The application configuration map.
        user_data: The in-memory user data containing User IDs and nicknames,
            or `None` if not yet loaded.
        sep: The separator string used to split raw User ID and nickname input.
    """

    def __init__(self, config: ConfigMap):
        """
        Initializes the `PlayerTracker` class with the provided configuration.

        Args:
            config: The application configuration map used to drive
                service behaviour such as chunk sizes, limits, and separators.
        """

        self.config = config
        self.user_data: UserData | None = None

        self.sep = self.config["SEPARATOR"]

    def _has_reached_user_limit(self, user_ids: UserIds) -> bool:
        """Returns `True` if the number of User IDs exceeds the configured maximum."""
        return len(user_ids) > self.config["MAX_USER_IDS"]

    @log_lifecycle(
        start="Starting payload parsing and validation process.",
        end="Payload parsing and validation completed.",
    )
    def _parse_and_validate(
        self,
        raw_user_ids: RawUserIds | None = None,
        raw_user_names: RawUsernames | None = None,
        append: bool = False,
    ) -> Result[UserIds | None, Usernames | None]:
        """
        Parses and validates raw User IDs and nickname input, checking
        combined capacity against the limit when `append` is `True`.
        """

        parsed_user_ids = None
        parsed_user_names = None

        if raw_user_ids is not None:
            _LOGGER.info("Parsing raw User ID(s) from user input.")

            parsed_user_ids = self._parse_user_ids(raw_user_ids, self.sep)
            if not parsed_user_ids:
                return Result.err(UserIdError.INVALID_USER_IDS)

            if self._has_reached_user_limit(parsed_user_ids):
                return Result.err(UserIdError.USER_QUOTA_EXCEEDED)

            if append:
                _LOGGER.info("Starting maximum capacity check for storing User IDs.")

                user_data = self.user_data
                if user_data is None:
                    return Result.err(CommonError.unexpected())

                # Ensure the combined size of the current and incoming lists does not
                # exceed the maximum allowed capacity before appending new User IDs
                combined_user_ids = user_data[USER_IDS_KEY] + parsed_user_ids

                if self._has_reached_user_limit(combined_user_ids):
                    return Result.err(UserIdError.INVALID_USER_ID_FORMAT)

        if raw_user_names is not None:
            _LOGGER.info("Parsing raw nicknames from user input.")

            parsed_user_names = self._parse_user_names(
                raw_user_names, self.sep, self.config["MAX_CHAR_USER_NAME"]
            )

            total_user_names = len(parsed_user_names)

            # Convert to a set to efficiently remove any duplicate User IDs
            if parsed_user_ids is not None and total_user_names != len(
                set(parsed_user_ids)
            ):
                return Result.err(UsernameError.USER_ID_AND_NAME_MISMATCH)

            if total_user_names < 1:
                return Result.err(UsernameError.MISSING_USER_NAMES)

        return Result.ok(parsed_user_ids, parsed_user_names)

    @staticmethod
    def _parse_user_ids(raw_user_ids: RawUserIds, sep: str) -> UserIds:
        """
        Splits and casts a separator-delimited string of User IDs into
        a validated integer list.
        """

        # Discards any value that _cast_user_id deems invalid,
        # such as non-integers or out of range values
        return [
            user_id
            for value in raw_user_ids.split(sep)
            if (user_id := _cast_user_id(value)) is not None
        ]

    @staticmethod
    def _parse_user_names(
        raw_user_names: RawUsernames, sep: str, max_chars: int
    ) -> Usernames:
        """
        Splits a separator-delimited string of nicknames and truncates
        each to the character limit.
        """

        return [user_name[:max_chars] for user_name in raw_user_names.split(sep)]

    @log_lifecycle(
        start="Preparing payload construction.",
        end="Payload construction preparation complete.",
    )
    def _build_payloads(self, user_ids: UserIds) -> Payloads:
        """
        Splits User IDs into chunk-sized batches and wraps each in a `Payload` dict.
        """

        chunk_size = self.config["CHUNK_SIZE"]
        return [
            {_USER_IDS: user_ids[index : index + chunk_size]}
            for index in range(0, len(user_ids), chunk_size)
        ]

    @log_lifecycle(
        start="Preparing payload submission.",
        end="Payload submission preparation complete.",
    )
    def _submit_payloads(
        self, executor: ThreadPoolExecutor, payloads: Payloads
    ) -> list[Future[FetchResult]]:
        """Submits each payload to the thread pool and returns the resulting futures."""

        return [
            executor.submit(_fetch_presence, _TARGET_URL, payload) for payload in payloads
        ]

    def get_totals(self, user_ids: UserIds) -> tuple[int, int]:
        """
        Calculates the total number of API chunks and User IDs for a given list.

        Args:
            user_ids: The list of User IDs to calculate totals for.

        Returns:
            total_chunks: The number of batched API requests required based on the
                configured chunk size.

            total_user_ids: The total number of User IDs in the provided list.
        """

        total_user_ids = len(user_ids)
        return ceil(total_user_ids / self.config["CHUNK_SIZE"]), total_user_ids

    def _load_existing_user_data(self) -> Result:
        """
        Reads and sanitizes persisted user data from disk and assigns
        it to `user_data`.
        """

        _LOGGER.info("Fetching JSON contents and configuring class attributes.")

        fetch_result = fetch_json(USER_DATA_PATH)
        if not fetch_result.success:
            return Result.err(fetch_result.error)

        user_data = cast(
            UserData,
            sanitize_with_template(
                data=fetch_result.payload[0],  # type: ignore[assignment]
                template=_USER_DATA_TEMPLATE,
                ignored_keys=(USER_NAMES_KEY),
            ),
        )

        self.user_data = user_data
        return Result.ok()

    def _initialize_user_data(self, raw_user_ids: RawUserIds) -> Result:
        """
        Parses raw User IDs, writes a fresh user data file to disk,
        and assigns it to `user_data`.
        """

        _LOGGER.info(
            "Parsing, validating raw User ID(s), and configuring class attributes."
        )

        validation_result = self._parse_and_validate(raw_user_ids)
        if not validation_result.success:
            return Result.err(validation_result.error)

        user_data: UserData = {
            USER_IDS_KEY: validation_result.payload[0] or [],
            USER_NAMES_KEY: {},
        }
        write_result = write_json(USER_DATA_PATH, user_data)

        if not write_result.success:
            return Result.err(write_result.error)

        self.user_data = user_data

        return Result.ok()

    @log_lifecycle(
        start="Starting JSON read and write cycle for user data processing.",
        end="JSON read and write cycle for user data processing completed.",
    )
    def load_user_data(self, raw_user_ids: RawUserIds | None = None) -> Result:
        """
        Loads or initializes user data depending on whether raw input is provided.

        If `user_data` is already populated, this method returns early without
        making any changes. If `raw_user_ids` is provided, the data is parsed,
        validated, and written to disk as a fresh file.

        Otherwise, existing persisted data is read from disk.

        Args:
            raw_user_ids: A raw separator-delimited string of User IDs to
                initialize tracking with. If `None`, existing data is loaded
                from disk instead.

        Returns:
            Result: A `Result` instance indicating whether user data was
                successfully loaded or initialized.
        """

        if self.user_data is not None:
            _LOGGER.warning(
                "User data already exists. Skipping load or overwriting existing data."
            )
            return Result.ok()

        if raw_user_ids is None:
            return self._load_existing_user_data()

        return self._initialize_user_data(raw_user_ids)

    @require_success
    @log_lifecycle(
        start="Syncing in-memory user data to JSON.",
        end="Successfully wrote in-memory user data to JSON.",
    )
    def _write_user_to_disk(self) -> Result:
        """Persists the current in-memory `user_data` to the JSON file on disk."""

        user_data = self.user_data
        if user_data is None:
            return Result.err(CommonError.unexpected())

        result = write_json(USER_DATA_PATH, user_data)
        if not result.success:
            return Result.err(result.error)

        return Result.ok()

    @log_lifecycle(
        start="Appending raw User ID to user data.",
        end="Successfully appended raw User ID to user data.",
    )
    def add_user_id(self, raw_user_id: RawUserIds, user_ids: UserIds) -> Result:
        """
        Validates and appends a single User ID to the list.

        Args:
            raw_user_id: The raw string representation of the User ID to add.
            user_ids: The current in-memory list of User IDs to append to.

        Returns:
            Result: A `Result` instance indicating whether the User ID was
                successfully added and persisted.
        """

        result = self._parse_and_validate(raw_user_id, append=True)
        if not result.success:
            return Result.err(result.error)

        parsed_user_ids = result.payload[0] or []
        first_user_id = parsed_user_ids[0]

        if first_user_id in user_ids:
            return Result.err(UserIdError.USER_ID_EXISTS)

        user_ids.append(first_user_id)
        self._write_user_to_disk()

        return Result.ok()

    @log_lifecycle(
        start="Removing raw User ID from user data.",
        end="Successfully removed raw User ID from user data.",
    )
    def remove_user_id(self, raw_user_id: RawUserIds, user_ids: UserIds) -> Result:
        """
        Validates and removes a single User ID from the list.

        Args:
            raw_user_id: The raw string representation of the User ID to remove.
            user_ids: The current in-memory list of User IDs to remove from.

        Returns:
            Result: A `Result` instance indicating whether the User ID was
                successfully removed and persisted.
        """

        result = self._parse_and_validate(raw_user_id)
        if not result.success:
            return Result.err(result.error)

        parsed_user_ids: UserIds = result.payload[0] or []
        first_user_id = parsed_user_ids[0]

        if first_user_id not in user_ids:
            return Result.err(UserIdError.MISSING_USER_ID)

        user_ids.remove(first_user_id)
        self._write_user_to_disk()

        return Result.ok()

    @log_lifecycle(
        start="Adding nickname with assigned User ID to user data.",
        end="Successfully added nickname with assigned User ID to user data.",
    )
    def add_user_names(
        self,
        user_ids: UserIds,
        user_names: UsernameMap,
        raw_user_ids: RawUserIds,
        raw_user_names: RawUsernames,
    ) -> Result:
        """
        Assigns or updates nicknames for a set of User IDs.

        Parses and validates both the raw User IDs and nicknames, then maps
        each nickname to its corresponding User ID.

        Only User IDs that are already present in the list are updated.

        Args:
            user_ids: The current in-memory list of User IDs used to
                filter which nicknames are applied.

            user_names: The current in-memory nickname map to update.

            raw_user_ids: A raw separator-delimited string of User IDs to
                assign nicknames to.

            raw_user_names: A raw separator-delimited string of nicknames
                in the same order as `raw_user_ids`.

        Returns:
            Result: A `Result` instance indicating whether the nicknames
                were successfully updated and persisted.
        """

        result = self._parse_and_validate(
            raw_user_ids=raw_user_ids, raw_user_names=raw_user_names, append=True
        )

        if not result.success:
            return Result.err(result.error)

        parsed_user_ids: UserIds = result.payload[0] or []
        parsed_user_names: Usernames = result.payload[1] or []

        # User IDs are cast to str for JSON compatibility before being stored
        user_names.update(
            {
                str(user_id): parsed_user_names[index].strip()
                for index, user_id in enumerate(parsed_user_ids)
                if user_id in user_ids
            }
        )

        self._write_user_to_disk()

        return Result.ok()

    @log_lifecycle(
        start="Removing nickname and its assigned User ID from user data.",
        end="Successfully removed nickname and its assigned User ID from user data.",
    )
    def remove_user_names(
        self,
        user_names: UsernameMap,
        raw_user_ids: RawUserIds,
    ) -> Result:
        """
        Removes nicknames for a set of User IDs from the nickname map.
        Silently skips any User ID that does not have an associated nickname.

        Args:
            user_names: The current in-memory nickname map to update.
            raw_user_ids: A raw separator-delimited string of User IDs whose
                nicknames should be removed.

        Returns:
            Result: A `Result` instance indicating whether the nicknames
                were successfully removed and persisted.
        """

        result = self._parse_and_validate(raw_user_ids)
        if not result.success:
            return Result.err(result.error)

        parsed_user_ids: UserIds = result.payload[0] or []
        for user_id in parsed_user_ids:
            # None prevents a KeyError if the User ID has no associated nickname
            user_names.pop(str(user_id), None)

        self._write_user_to_disk()

        return Result.ok()

    @log_lifecycle(
        start="Building and submitting payloads using the future objects iterator.",
        end="Successfully built and submitted all payloads via future objects iterator.",
    )
    def fetch_presences(
        self, user_ids: UserIds, on_progress: Callable[..., Any] | None = None
    ) -> Result[ParsedData]:
        """
        Fetches player presence data from the Roblox API using concurrent requests.

        Splits User IDs into batched payloads and dispatches them concurrently
        via a thread pool. Collects all responses and parses them into a unified
        presence map.

        Args:
            user_ids: The list of User IDs to fetch presence data for.
            on_progress: An optional callable invoked after each completed
                batch, typically used to advance a progress bar.

        Returns:
            Result: A `Result` instance containing the parsed presence data
                as `ParsedData`, or an error if any request failed.
        """

        payloads = self._build_payloads(user_ids)
        responses: list[Response] = []

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = self._submit_payloads(executor, payloads)

            _LOGGER.info("Iterating through future objects.")

            # as_completed yields futures in completion order, not submission order
            # start=1 is used for human-readable batch logging (e.g. batch [1] not [0])
            for index, future in enumerate(as_completed(futures), start=1):
                # future.result() blocks until the future completes
                response: FetchResult = future.result()
                if not response.success:
                    return Result.err(response.error)

                responses.append(response.payload[0])

                if on_progress is not None:
                    on_progress()

                _LOGGER.info(f"Payload batch [{index}] completed successfully.")

        return Result.ok(_parse_presences(responses))

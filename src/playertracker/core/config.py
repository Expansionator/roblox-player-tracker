# config.py

"""
Contains the default configuration settings for the application.

This module defines global constants, system limits, and formatting settings
used to control application isolation, input data parsing, and API request batching.

Attributes:
    PROGRAM_ID: A unique GUID used to ensure the application directory
        remains isolated.
    SEPARATOR: Separator used for splitting User IDs and nicknames (e.g., ",").
    MAX_USER_IDS: Maximum number of User IDs that can be stored in the JSON.
    CHUNK_SIZE: Number of User IDs included per API request when batching.
    MAX_CHAR_USER_NAME: Maximum number of characters allowed for user nicknames.
"""

from __future__ import annotations

from typing import Final, TypedDict

PROGRAM_ID: Final[str] = "df8239be-430d-43d1-bf6a-b15fab61c6ff"


class ConfigMap(TypedDict):
    PROGRAM_ID: str
    SEPARATOR: str

    MAX_USER_IDS: int
    CHUNK_SIZE: int
    MAX_CHAR_USER_NAME: int


DEFAULT_CONFIG: ConfigMap = {
    "PROGRAM_ID": PROGRAM_ID,
    "SEPARATOR": ",",
    "MAX_USER_IDS": 100,
    "CHUNK_SIZE": 5,
    "MAX_CHAR_USER_NAME": 30,
}

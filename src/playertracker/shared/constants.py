# constants.py

"""
Constants used throughout the program, primarily in `app.py` and `service.py`.

These constants define the keys used for storing and retrieving data in JSON
structures, ensuring consistency across different parts of the application.
"""

from __future__ import annotations

from typing import Final

USER_IDS_KEY: Final = "user_ids"
USER_NAMES_KEY: Final = "user_names"

PRESENCE_TYPE_KEY: Final = "presence_type"

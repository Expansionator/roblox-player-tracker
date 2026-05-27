# sanitizer.py

"""
Utilities for sanitizing untrusted dict and list data against a template schema.

Ensures loaded JSON payloads (such as config files) conform to expected
types and structure before use, falling back to template defaults for
any missing or invalid values.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy

from playertracker.shared.decorators import log_lifecycle

type GenericDict[K, V] = dict[K, V]
type GenericList[T] = list[T]

type DataStructure[K, V, T] = GenericDict[K, V] | GenericList[T]

type IgnoredKeys = Sequence[str]


@log_lifecycle(start="Sanitizing raw data into structured dict using template.")
def _sanitize_dict[K, V, T](
    data: DataStructure[K, V, T],
    template: GenericDict[K, V],
    ignored_keys: IgnoredKeys | None = None,
) -> GenericDict[K, V]:
    """
    Recursively enforces a dict template onto raw data and
    handles nested structures.
    """

    new_data: GenericDict[K, V] = {}

    if not isinstance(data, dict) or not data:
        return deepcopy(template)

    for key, template_value in template.items():
        if key not in data:
            new_data[key] = template_value
            continue

        data_value = data[key]

        if ignored_keys is not None and key in ignored_keys:
            new_data[key] = data_value
            continue

        if isinstance(template_value, (list, dict)):
            new_data[key] = sanitize_with_template(data_value, template_value)  # type: ignore[arg-type]
            continue

        if not isinstance(data_value, type(template_value)):
            new_data[key] = template_value
            continue

        new_data[key] = data_value

    return new_data


@log_lifecycle(start="Sanitizing raw data using list template.")
def _sanitize_list[K, V, T](
    data: DataStructure[K, V, T], template: GenericList[T]
) -> GenericList[T]:
    """Validates list data structures against a fallback list template."""

    if not isinstance(data, list) or not data:
        return deepcopy(template)

    return data


@log_lifecycle(
    start="Preparing to sanitize raw data into structured format.",
    end="Successfully sanitized raw data into structured format.",
)
def sanitize_with_template[K, V, T](
    data: DataStructure[K, V, T],
    template: DataStructure[K, V, T],
    ignored_keys: IgnoredKeys | None = None,
) -> DataStructure[K, V, T]:
    """
    Sanitize unsafe dictionary or list inputs using a template schema.

    Dynamically routes data processing to either dictionary or list sanitization
    sub-routines based on the type of the provided template.

    Args:
        data: The raw, unvalidated JSON/Data payload.
        template: The expected blueprint schema (dict or list).
        ignored_keys: Dictionary keys that should skip type-safety checks.

    Returns:
        sanitized_data: Sanitized, type-safe data matching the template structure.

    Examples:
        >>> schema = {"name": "Unknown", "score": 0}
        >>> raw = {"name": "Alice", "score": "not_an_int!"}
        >>> sanitize_with_template(raw, schema)
        {'name': 'Alice', 'score': 0}
    """

    if isinstance(template, dict):
        return _sanitize_dict(data, template=template, ignored_keys=ignored_keys)

    return _sanitize_list(data, template)

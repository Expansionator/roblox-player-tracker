# hardware.py

"""
Utilities for collecting basic system and hardware specifications.
"""

from __future__ import annotations

import platform

import psutil


def get_hardware_info() -> str:
    """
    Retrieves basic system and hardware specifications.

    Queries the operating system, CPU core counts, total RAM, and available
    disk space on the current drive. If any metric fails to resolve due to
    an exception, it gracefully falls back to an "Unknown" label for that
    specific component.

    Returns:
        hw_info: A single string containing the collected hardware specifications,
        separated by pipe symbols (` | `).

    Example:
        >>> get_hardware_info()
        'OS: Windows 11 (AMD64) | CPU Cores: 8 Physical / 16 Logical | RAM: 16.0 GB |'
        'Free Disk: 245.3 GB'
    """

    specs: list[str] = []
    try:
        specs.append(
            f"OS: {platform.system()} {platform.release()} ({platform.machine()})"
        )
    except Exception:
        specs.append("OS: Unknown")

    try:
        phys_cores = psutil.cpu_count(logical=False)
        log_cores = psutil.cpu_count(logical=True)

        specs.append(f"CPU Cores: {phys_cores} Physical / {log_cores} Logical")

    except Exception:
        specs.append("CPU: Unknown")

    try:
        mem = psutil.virtual_memory()
        total_ram_gb = round(mem.total / (1024**3), 1)  # 1024^3 converts bytes to GB

        specs.append(f"RAM: {total_ram_gb} GB")

    except Exception:
        specs.append("RAM: Unknown")

    try:
        disk = psutil.disk_usage(".")
        free_gb = round(disk.free / (1024**3), 1)

        specs.append(f"Free Disk: {free_gb} GB")

    except Exception:
        specs.append("Free Disk: Unknown")

    return " | ".join(specs)

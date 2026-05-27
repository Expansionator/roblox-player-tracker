# Setup

This document covers how to get PlayerTracker running locally for development.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Git

## Getting Started

1. Clone the repository

```bash
git clone https://github.com/Expansionator/roblox-player-tracker.git
cd roblox-player-tracker
```

2. Install dependencies

```bash
uv sync
```

This installs both runtime and dev dependencies defined in `pyproject.toml`.

3. Run the app

```bash
uv run pt
```

## Project Structure

```
roblox-player-tracker/
├── assets/                 # Application icon (icon.ico)
├── docs/                   # Documentation
├── examples/               # Sample config.json and user_data.json for reference
├── src/
│   └── playertracker/
│       ├── actions/        # Create, Modify, View, Uninstall action classes
│       ├── cli/            # Terminal output and prompt utilities
│       ├── core/           # Config, cooldown, service, and session logic
│       ├── persistence/    # File paths and JSON storage
│       ├── shared/         # Constants, decorators, messages, and typedefs
│       ├── utils/          # Hardware info, logger, sanitizer, and status bar
│       ├── app.py          # Top-level application controller
│       └── main.py         # Entry point
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── main.spec               # PyInstaller build spec
├── pyproject.toml
└── README.md
```

## Dev Tools

PlayerTracker uses the following dev tools, all installed via `uv sync`:

| Tool | Purpose |
|---|---|
| `pyright` | Static type checking |
| `ruff` | Linting and formatting |
| `pytest` | Testing |
| `pyinstaller` | Building the standalone executable |

### Type Checking

```bash
uv run pyright
```

### Linting

```bash
uv run ruff check
```

### Formatting

```bash
uv run ruff format
```

### Running Tests

```bash
uv run pytest
```

## Building the Executable

To build a standalone `.exe`:

```bash
uv run pyinstaller main.spec
```

Refer to the [PyInstaller docs](https://pyinstaller.org/en/stable/) for build configuration details.

# Architecture

This document describes the architectural design, software layers, runtime lifecycle, and core engineering patterns of PlayerTracker.

## Architectural Overview

PlayerTracker is a structured, layered command-line interface (CLI) application built with Python 3.13. It is engineered with strict operational constraints: it is a single-instance Windows-only utility that relies on decoupled functional layers to handle process safety, data persistence, network concurrency, and interactive menu dispatching.

```
                  ┌───────────────────────────────┐
                  │       utils/logger.py         │ ◄─── (Global Exception Hook, Lazy rotating file logging,
                  │       utils/sanitizer.py      │        Sanitization of local data)
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────▼───────────────┐
                  │            main.py            │ ◄─── (OS Check, Mutex Lock,
                  └───────────────┬───────────────┘        Config Initialization)
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │          app.py (App)         │ ◄─── (Interactive CLI Engine,
                  └───────┬───────────────┬───────┘        Action Routing)
                          │               │
        ┌─────────────────┘               └─────────────────┐
        ▼                                                   ▼
┌───────────────┐                                   ┌───────────────┐
│   actions/    │                                   │     core/     │
│ (User Tasks)  │                                   │ (Rules/Logic) │
└───────┬───────┘                                   └───────┬───────┘
        │ (Create, Modify,                                  │ (config.py, session.py,
        │  View, Uninstall)                                 │  cooldown.py)
        │                                                   │
        │                                                   ▼
        │                                           ┌─────────────────┐
        │                                           │ core/service.py │ ◄─── (ThreadPoolExecutor,
        │                                           └───────┬─────────┘        Batching, Network I/O)
        │                                                   │
        └─────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │    persistence/   │ ◄─── (JSON/SQLite Disk Data,
                        └───────────────────┘       Sandbox Path Management)

```

The system separates pure business rules, interactive terminal commands, network dispatch orchestration, and disk drivers to ensure that logic errors do not trigger silent application state corruption.

## Component Layers

The application code is divided into highly decoupled subsystems, each responsible for an isolated scope of execution under the `src/playertracker/` path:

### 1. Entry Point & Lifecycle Orchestration

* **`main.py`**: Controls global bootstrapping. It sets the terminal window title to the application name, verifies the runtime operating system is Windows, binds the top-level exception handler to capture unhandled failures, and enforces single-instance process execution before preparing local directories and parsing configurations.
* **`app.py` (`App`)**: The core operational controller. It acts as the central state machine, initializing the terminal UI, managing navigation routing between menus, capturing user input configurations, evaluating app-wide execution barriers (such as network rate limits), and presenting consolidated data results.

### 2. User Tasks (`actions/`)

All actions are driven by an abstract base class that enforces consistency across interactive features:

* **`actions/base.py` (`BaseAction`)**: The abstract base class that all action implementations must inherit from. It standardizes how actions interface with the core `PlayerTracker` service layer, exposes global configurations, and extracts layout parameters like user delimiters.
* **`actions/create.py` (`CreateAction`)**: Coordinates the interactive CLI prompt workflow for capturing completely new batches of player accounts from the terminal input. It passes the validated input down to the persistence service layers for storage allocation.
* **`actions/modify.py` (`ModifyAction`)**: Facilitates updating, adding, or removing User IDs and human-readable nicknames from the player tracking catalog (`user_data.json`) using localized menu routing choices.
* **`actions/view.py` (`ViewAction`)**: Formats and renders tracked data to the screen in a clean tabular orientation. It partitions wide datasets into horizontal text lines capped at five users per terminal row for clean viewing layouts.
* **`actions/uninstall.py` (`UninstallAction`)**: Deletes the local data environment. To circumvent Windows file locks on running binaries, it launches a hidden background PowerShell loop that waits until the principal process stops completely before discarding the executable asset.

### 3. Domain Core Logic (`core/`)

* **`core/config.py`**: Establishes immutable foundational limits, cross-layer fallback maps, network request chunk sizes, input constraints, and the hardware-independent program identifier GUID string (`PROGRAM_ID`).
* **`core/cooldown.py` (`CooldownSystem`)**: A rate-limiting state barrier. It uses an embedded disk cache layer to calculate time differences between consecutive tracking attempts, preventing excessive Roblox API requests.
* **`core/session.py`**: Interacts with the Win32 kernel to maintain operating-system-level process boundaries.
* **`core/service.py` (`PlayerTracker`)**: Orchestrates the backend business operations. It maps abstract requests into physical actions, divides raw data files into valid payloads, coordinates safe execution thread maps, and drives parallel downstream fetches.

### 4. Presentation & Output Interface (`cli/`)

* **`cli/output.py`**: Manages rich text coloring, layout borders, and custom formatting themes using `rich.console`, alongside uniform terminal exit routines.
* **`cli/prompt.py`**: Collects terminal inputs, enforces integer parameters, and wraps validation choices to prevent unexpected errors during menu selections.

### 5. Data Persistence (`persistence/`)

* **`persistence/paths.py`**: Resolves explicit physical filesystem environments within `%LOCALAPPDATA%`, creating explicit sandbox directories using the GUID-based folder structure for logs, data structures, and database engines.
* **`persistence/storage.py`**: High-reliability JSON disk reader/writer module. Wraps raw hardware reads and writes in exception boundaries to protect long-term storage configurations and provides truncated paths for logs.

### 6. Cross-Cutting Utilities & Types (`shared/` & `utils/`)

* **`shared/typedefs.py`**: Consolidates type-safety rules, domain primitives, structural schemas, data layouts, and the functional wrapper object (`Result`).
* **`shared/messages.py`**: A centralized repository of structured error containers, allowing clear, standardized messaging across CLI presentation layers and diagnostic files.
* **`shared/decorators.py`**: Implements reusable aspect-oriented attributes, injecting lifecycle trace loggers, system termination workflows, and execution-interception logic into separate code blocks.
* **`shared/constants.py`**: Explicit structural key strings (`user_ids`, `user_names`, `presence_type`) utilized for maintaining parsing invariants across file I/O operations and API mappings.
* **`utils/logger.py` (`LazyLogger`)**: Implements a lazy logger that defers file handler creation until its first execution call. It enforces a `utf-8` encoding schema to eliminate encoding issues on Windows environments and manages file rotations with explicit sizes and backups.
* **`utils/hardware.py`**: Gathers fundamental runtime technical metrics about the host machine (OS layout, physical/logical CPU core configurations, memory sizes, and free disk volumes) to feed system diagnostics.
* **`utils/sanitizer.py`**: Validates unverified list and dictionary payloads against expected template structures, silently substituting missing keys with default fallback items.
* **`utils/status.py`**: Wraps the rendering loops inside a styled context manager driven by `alive_progress` to display responsive visual feedback during operations.

## Core Engineering Patterns

### Functional Error Handling via `Result` Containers

PlayerTracker completely avoids letting standard runtime errors bubble up and cause uncontrolled application crashes. Instead, it adopts a functional program-design pattern, wrapping operational outcomes in an immutable `Result` generic container.

```python
@dataclass(frozen=True, kw_only=True)
class Result[*Ts = *tuple[Any, ...]]:
    success: bool
    payload: tuple[*Ts, ...] | tuple[()]
    error: str | None

```

Functions across core layers return a successful state containing unpacked payload structures (`Result.ok(data)`) or capture explicit failure points (`Result.err(message)`). This ensures the application can safely halt processing and gracefully show clean error screens to the user.

### Aspect-Oriented Execution Barriers

Decorators are heavily utilized as execution barriers to keep business logic clean and readable:

* **`@require_success`**: Placed on top of internal operational steps. It automatically inspects the returning functional container. If `success` is `False`, it immediately halts the runtime flow and passes the precise error diagnostic down to the UI exit sequence.
* **`@log_lifecycle`**: Automatically tracks and logs system boundaries without manual entry injections inside the actual execution loops.

### Win32 Process Locking & Instance Isolation

To prevent race conditions on files or resource conflicts, the program uses OS-level process isolation inside `core/session.py`:

| Component | WinAPI Call | System Object | Mechanism |
| --- | --- | --- | --- |
| **Instance Verification** | `ctypes.windll.kernel32.CreateMutexW` | Named System Mutex | Uses a global unique string (`PROGRAM_ID`) to register an exclusive system handle. If the kernel flags an existing allocation (`ERROR_ALREADY_EXISTS`), execution safely halts. |

## Data Flow & Concurrency Model

PlayerTracker utilizes a concurrent, batch-allocated processing model to optimize network speed while respecting remote endpoints.

### Concurrent Processing Engine

When a tracking cycle is triggered through `app.py`, execution moves through a highly managed pipeline across multiple modules:

```
[ User List ] ──► [ Chunk Payloads ] ──► [ ThreadPoolExecutor ] ──► [ Roblox Presence API ]
   (100 IDs)          (Groups of 5)          (Max 5 Workers)            (Concurrent POSTs)

```

1. **Payload Splitting:** `PlayerTracker._build_payloads` inside `core/service.py` takes the total list of configured User IDs (up to `MAX_USER_IDS`) and partitions them into small chunks defined by `CHUNK_SIZE` (defaulting to 5 IDs per batch).
2. **Thread Allocation:** An internal `ThreadPoolExecutor` spawns up to a maximum worker limit (`_MAX_WORKERS = 5`) to manage parallel tracking jobs.
3. **Asynchronous Execution Loops:** Payloads are bound to network workers via `requests.Session` and dispatched concurrently. Futures are consumed as they finish (`as_completed`), which updates a progress bar in the terminal real-time.
4. **Data Aggregation:** Completed payload chunks are parsed, filtered, and aggregated into a single, unified state model (`ParsedData`) before being handed back to the UI render engine.

### Cooldown Storage Architecture

The rate-limiting system inside `core/cooldown.py` uses a localized disk cache (`diskcache.Cache`) backed by a lightweight SQLite instance inside `%LOCALAPPDATA%`.

When a user initiates tracking, the application performs an instantaneous timestamp evaluation against the database records. If the duration since the last query is less than the required fallback window (`_COOLDOWN_PERIOD = 90.0` seconds), the execution layer halts immediately, protecting remote network resources.

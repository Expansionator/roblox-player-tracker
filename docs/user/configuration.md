# Configuration

PlayerTracker stores a configuration file that controls certain behaviours of the app. This file is created automatically on first run and *does not need to be touched* for normal use.

## Config File Location

```
%LOCALAPPDATA%\PlayerTracker\<program-id>\config.json
```

To open it, paste the path above into File Explorer's address bar and replace `<program-id>` with the folder name inside `PlayerTracker\`.

## Settings

### `SEPARATOR`

The character used to split User IDs and nicknames when entering multiple values.

| Default | Allowed values |
|---|---|
| `,` | Any single character |

### `MAX_USER_IDS`

The maximum number of User IDs that can be tracked at once.

| Default | Recommended range |
|---|---|
| `100` | 10 – 100 |

> **Warning:** Setting this too high will significantly slow down fetch times, as PlayerTracker has to make more API requests to Roblox. Keep it to what you actually need.

### `MAX_CHAR_USER_NAME`

The maximum number of characters allowed for a nickname.

| Default | Recommended range |
|---|---|
| `30` | 5 – 30 |

> **Warning:** Long nicknames will clutter the results display and make it harder to read at a glance. Keep nicknames short and recognizable.

## Manual Editing

The config file can be edited manually in any text editor, but this is **not recommended**. Invalid values may cause unexpected behaviour or be silently reset to their defaults on next launch.

It is safer to let the app manage these settings where possible.

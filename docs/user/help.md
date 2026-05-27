# Help

This page covers common issues, error messages, and tips to get PlayerTracker working correctly.

## Before You Start

- **Internet connection is required.** PlayerTracker fetches player statuses directly from Roblox's servers.
- **User IDs must be valid.** A User ID is a positive whole number greater than 0 (e.g., `1`, `10001`). Usernames are not accepted.
- **Windows only.** PlayerTracker does not support macOS or Linux.

## Common Issues

### Player is always showing Offline

Roblox's presence API respects each player's privacy settings. If a player has set their presence to private, PlayerTracker will always show them as Offline. This is a Roblox limitation and not a bug.

### Results feel slow or take a long time

This is expected when tracking a large number of User IDs. PlayerTracker batches API requests to Roblox, so the more players you track, the longer it takes. Consider keeping your list to what you actually need.

### The app won't let me fetch again immediately

PlayerTracker has a built-in cooldown between fetches to avoid overloading Roblox's servers. If you try too soon, you will see a message like:

```
Please wait 2 min and 30 sec before running the application again.
```

Wait for the cooldown to expire and try again.

### The app says it's already running

```
The application is already running.
```

Only one instance of PlayerTracker can run at a time. Check your taskbar or Task Manager for an existing window and close it before launching again.

## Error Messages

| Message | What it means |
|---|---|
| `Too many provided, or one or more User ID(s) are invalid.` | One or more of the User IDs you entered don't exist on Roblox, or you entered too many at once. |
| `No valid User ID(s) were found. Please check that your IDs are correct and try again.` | The format of your input was incorrect. Make sure you're entering numbers separated by commas. |
| `That User ID already exists.` | You tried to add a User ID that is already in your tracked list. |
| `That User ID doesn't exist.` | You tried to remove a User ID that isn't in your tracked list. |
| `You've reached the maximum number of User IDs.` | You've hit the tracking limit. Remove a User ID before adding a new one. |
| `The number of nicknames must match the number of User IDs.` | When adding nicknames, the count of nicknames must equal the count of User IDs you entered. |
| `The request timed out.` | PlayerTracker couldn't reach Roblox. Check your internet connection and try again. |
| `Could not reach the server.` | Same as above, no connection to Roblox's servers. |
| `The server returned an unexpected response.` | Roblox's API returned an error. This is usually temporary, try again later. |
| `Can't access [file] because it's open in [app].` | A file PlayerTracker needs is locked by another program. Close that program and try again. |
| `The file appears to be corrupted or has an invalid format.` | A data file has been manually edited or damaged. See the reset steps below. |

## Resetting the App

If things start behaving unexpectedly, a clean reset usually fixes it.

1. **Close PlayerTracker completely** before doing anything
2. Navigate to `%LOCALAPPDATA%\PlayerTracker\<program-id>\`
3. Delete `user_data.json` to reset your tracked User IDs, or `config.json` to reset your configuration
4. Relaunch the app. The deleted files will be recreated automatically

> **Note:** Deleting `user_data.json` will permanently remove all your saved User IDs and nicknames.

## Using the Log File

PlayerTracker generates an `app.log` file that records what the app was doing during a session. If you're experiencing a persistent issue, the log can help identify what went wrong.

The log file is located at:

```
%LOCALAPPDATA%\PlayerTracker\<program-id>\app.log
```

If you're reporting a bug on [GitHub Issues](https://github.com/Expansionator/roblox-player-tracker/issues), attaching your `app.log` helps a lot.

## Still Stuck?

Open an issue on [GitHub](https://github.com/Expansionator/roblox-player-tracker/issues) and include:

- What you were doing when the issue occurred
- The error message you saw (if any)
- Your `app.log` file

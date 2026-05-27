# Getting Started

PlayerTracker is a CLI tool that lets you monitor Roblox player statuses (Offline, Online, Playing) across a customizable list of User IDs.

## Installation

1. Head to the [Releases](https://github.com/Expansionator/roblox-player-tracker/releases) page
2. Download the latest executable
3. Place it somewhere convenient on your machine

## First Run

Open a terminal, navigate to where you placed the executable, and run it. You will be greeted with the main menu.

> **Note:** Results depend on each player's privacy settings and may not always be available.

## Main Menu

When you launch `PlayerTracker`, you will be presented with three options:

- **Create:** Enter User IDs to track for the first time
- **Load:** Load your previously saved User IDs
- **Uninstall:** Permanently remove all application data

## Create

Select **Create** if this is your first time or you want to start fresh.

You will be prompted to enter one or more User IDs separated by commas:

```
Enter User ID(s): 10001, 10002, 10003
```

Once saved, the app will proceed to fetch their statuses.

## Load

Select **Load** to use your previously saved User IDs.

After loading, you will be asked how you want to proceed:

- **Continue:** Fetch statuses immediately
- **Modify:** Edit your User IDs or nicknames before fetching
- **View:** See your currently tracked User IDs before fetching

### Modify

Selecting **Modify** gives you two options:

**User ID**
- Add a User ID to your current list
- Remove a User ID from your current list

**Nickname**
- Add or update nicknames for one or more User IDs
- Remove nicknames from one or more User IDs

When adding nicknames, enter the User IDs and their nicknames in the **same order**, separated by commas:

```
Enter User ID(s): 10001, 10002
Enter Nickname(s): John, Bob
```

### View

Displays your currently tracked User IDs in a grid, up to 5 per row. Nicknames are shown alongside their User ID if assigned.

## Results

After fetching, `PlayerTracker` displays a **Player Summary** showing the count and percentage of players per status:

```
Playing  : 2 (40%)
Online   : 1 (20%)
Offline  : 2 (40%)
```

You will then be asked:

- **View details:** Shows each player's User ID, nickname (if set), and their current status
- **Exit:** Closes the app

## Uninstall

Select **Uninstall** from the main menu to permanently remove all local application data including your saved User IDs and logs.

You will be asked to confirm before anything is deleted. This action is irreversible.

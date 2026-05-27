# Presence Reference

This document covers the Roblox Presence API used by PlayerTracker, including the endpoint, request and response structure, raw presence type values, and how they map internally to display statuses.

## Endpoint

PlayerTracker sends POST requests to the Roblox presence endpoint to retrieve player statuses:

```
POST https://presence.roblox.com/v1/presence/users
```

User IDs are sent in batches determined by `CHUNK_SIZE` in the config.

### Request

```json
{
  "userIds": [10001, 10002, 10003]
}
```

### Response

```json
{
  "userPresences": [
    {
      "userPresenceType": 2,
      "lastLocation": "Some Experience",
      "placeId": 123456,
      "rootPlaceId": 123456,
      "gameId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "universeId": 654321,
      "userId": 10001,
      "lastOnline": "2024-01-01T00:00:00.000Z"
    }
  ]
}
```

PlayerTracker consumes `userPresenceType` and `userId` from each entry. All other fields are currently unused.

## Presence Types

The `userPresenceType` field is an integer with the following values as defined by Roblox:

| Value | Roblox Label |
|---|---|
| `0` | Offline |
| `1` | Online |
| `2` | InGame |
| `3` | InStudio |
| `4` | Invisible |

## Internal Mappings

PlayerTracker collapses the five Roblox presence types into three display statuses, defined in `_PRESENCE_MAP` and `_COLOR_PRESENCE_MAP` in `app.py`:

| `userPresenceType` | Roblox Label | Display Status | Theme Key |
|---|---|---|---|
| `0` | Offline | Offline | `offline` |
| `1` | Online | Online | `online` |
| `2` | InGame | Playing | `playing` |
| `3` | InStudio | Online | `online` |
| `4` | Invisible | Offline | `offline` |

- `InStudio` (`3`) maps to **Online** since the user is active in a Roblox environment
- `Invisible` (`4`) maps to **Offline** as the user has hidden their presence

Any `userPresenceType` value outside the expected range falls back to **Offline** via the bounds check in `_group_by_presence`.

## Privacy Behaviour

Roblox enforces user privacy settings at the API level. If a user has restricted their presence, the API returns `userPresenceType: 0` regardless of their actual activity. There is no way to distinguish a private user from a genuinely offline one.

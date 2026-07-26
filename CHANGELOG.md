# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.0] - 2026/07/27

### Fixed

- Resolved an unhandled `KeyError` exception that crashed the app when preparing the player summary.
- Fixed an `IndexError` crash when rendering player details for players with a status of 'Studio'.

[v1.0.0]: https://github.com/Expansionator/roblox-player-tracker/releases/tag/v1.0.0

## [v0.1.0] - 2026/05/27

### Added

- Initial release of **PlayerTracker**, a CLI tool for Roblox users to monitor
  player statuses (Offline, Online, Playing) across a customizable list of UserIDs.

[v0.1.0]: https://github.com/Expansionator/roblox-player-tracker/releases/tag/v0.1.0

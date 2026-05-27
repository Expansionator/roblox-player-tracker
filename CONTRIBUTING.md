# Contributing to PlayerTracker

Thanks for your interest in contributing! This document outlines how to get involved.

## Prerequisites
 
Before contributing, make sure you have:

- Python 3.13 installed
- [uv](https://docs.astral.sh/uv/) installed
- Git installed
- A GitHub account

## Getting Started

1. Fork the repository
2. Clone your fork

```bash
git clone https://github.com/Expansionator/roblox-player-tracker.git
cd roblox-player-tracker
```

3. Install dependencies

```bash
uv sync
```

## How to Contribute

1. Create a new branch for your change

```bash
git switch -c feature/your-feature-name
```

2. Make your changes
3. Commit with a clear message

```bash
git add .
git commit -m "brief description of what you did"
```

4. Push to your fork

```bash
git push origin feature/your-feature-name
```

5. Open a pull request against the `main` branch and describe what your change does and why.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/Expansionator/roblox-player-tracker/issues) and include:

- Steps to reproduce the bug
- What you expected to happen
- What actually happened
- Your OS and Python version
- Your `app.log` file if relevant

## Suggesting Features

Open a [GitHub Issue](https://github.com/Expansionator/roblox-player-tracker/issues) with the label `enhancement` and describe the feature and the problem it solves. Since this is a solo project, not all suggestions will be accepted, but all are welcome.

## Code Style

- Keep code readable and consistent with the existing style
- Use clear, descriptive variable and function names
- Add comments where the logic isn't immediately obvious

## Please Avoid

- Opening pull requests for minor typo fixes
- Submitting large refactors without discussing them in an issue first
- Changing unrelated files in your pull request

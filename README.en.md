# Private Game Translator

[中文](./README.md) | [English](./README.en.md)

A local translation-helper prototype for `Unity Mono` game directories, built with Python.

Current scope:

- Supports `Unity Mono` only
- Does not support `Unity IL2CPP`
- Does not support other game engines
- Does not aim to be a universal text capture or OCR translation tool

This repository currently fits best as:

- a `Unity Mono` runtime installer prototype
- a localization workflow validation tool
- a desktop wrapper example for local translation tooling

Detailed documentation:

- [Usage Guide](./docs/USAGE.en.md)
- [Chinese Usage Guide](./docs/USAGE.md)

## Repository Scope

This repository is mainly for source code and project structure. It is not intended to be a public redistribution bundle for third-party runtime binaries.

Please keep these boundaries in mind:

- Source code can stay in the repository
- Local user settings, caches, and packaged build outputs should stay out of version control
- Third-party runtime files, patchers, fonts, and DLLs may have separate license or redistribution restrictions
- If you plan to publish this project publicly, it is safer to require users to prepare third-party runtime files themselves

## Current Capabilities

- Detect supported `Unity Mono` game directory structures
- Inspect target game directories and runtime directories
- Import runtime resources from a prepared source game directory
- Generate `AutoTranslator\Config.ini` for the target game
- Install runtime files into the target game
- Uninstall and roll back files written by the tool
- Run a local HTTP translation bridge
- Support both LLM mode and machine-translation mode
- Cache translation results locally
- Provide a `PySide6` desktop UI for common operations

## Not Included Yet

- Generic `IL2CPP` support
- OCR-based text extraction
- Online setup wizard
- Third-party runtime license packaging guidance
- A universal workflow for all game types

## Installation

Requirements:

- Windows
- Python `3.12+`

Install the project:

```powershell
python -m pip install -e .
```

## Quick CLI Examples

Inspect a game directory:

```powershell
python main.py inspect-game "D:\Path\To\YourGame"
```

Inspect a runtime directory:

```powershell
python main.py inspect-runtime --runtime-root "D:\Path\To\runtime\unity_mono"
```

Import runtime resources:

```powershell
python main.py import-runtime `
  --source-game "D:\Path\To\SourceGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono"
```

Dry-run installation:

```powershell
python main.py install `
  --game "D:\Path\To\YourGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono" `
  --target-language zh `
  --dry-run
```

Uninstall:

```powershell
python main.py uninstall --game "D:\Path\To\YourGame"
```

## GUI

Launch the desktop UI:

```powershell
python main_gui.py
```

Or:

```powershell
game-translator-gui
```

## Local Settings and Cache

The tool may create local runtime data such as:

- `.private_translator/settings.json`
- `.private_translator/translation_cache.json`

These files are local user data and should not be committed to a public repository.

## Packaging

To build the desktop executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_gui.ps1
```

Default output:

```text
dist/PrivateGameTranslator/PrivateGameTranslator.exe
```

## Project Structure

```text
src/game_translator/
tests/
main.py
main_gui.py
build_gui.ps1
PrivateGameTranslator.spec
```

## Publishing Notes

If you want to make this a cleaner public GitHub repository, the next good steps are:

1. Add a `LICENSE`
2. Clarify redistribution boundaries for third-party runtime files
3. Rename project/package metadata away from `private` and `MVP`
4. Make third-party runtime files user-provided instead of repository-bundled
5. Add sanitized example configuration guidance

## Disclaimer

This project is for localization workflow research, desktop tooling, and runtime-installation flow validation.

Before using it with third-party games, please verify:

- the game's user agreement
- the license of any patcher or runtime component
- redistribution rights for fonts, DLLs, config templates, and related assets

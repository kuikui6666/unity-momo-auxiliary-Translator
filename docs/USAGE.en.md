# Usage Guide

[中文](./USAGE.md) | [English](./USAGE.en.md)

This guide is written for first-time visitors to the project. Its goal is to help you quickly understand, from the GitHub repository alone:

- what this tool does
- what kinds of games it supports
- what you need to prepare before using it
- what order of operations is recommended
- how to reason about common failures

## 1. Confirm the Supported Scope First

This project currently supports `Unity Mono` games only.

You can think of it as a localization-helper tool built around a directory structure like this:

- the game root contains `Game.exe`
- the same level contains `Game_Data`
- `Game_Data` contains `Managed`
- some games also include `MonoBleedingEdge`

This project does not currently apply to:

- `Unity IL2CPP`
- non-Unity games
- generic OCR/screen-capture translation workflows
- arbitrary Windows program text injection

If the target directory does not contain `*_Data/Managed`, it is probably not something this tool supports right now.

## 2. Core Workflow of the Tool

This project does not repack all game resources, and it does not directly rewrite every game text file.

Its current workflow is closer to this:

1. Detect whether the target game is a supported `Unity Mono` game
2. Prepare a usable translation runtime directory
3. Install the required runtime files into the target game
4. Generate `AutoTranslator\Config.ini` for the target game
5. Start the local translation bridge service
6. Let the game runtime request translations through the local endpoint
7. Cache translation results locally to reduce repeated requests

## 3. What You Need to Prepare

Before using the tool, you should prepare at least the following:

### 3.1 Python Environment

- Windows
- Python `3.12+`

### 3.2 A Supported Game Directory

The target game directory should look roughly like this:

```text
YourGame/
  YourGame.exe
  YourGame_Data/
    Managed/
```

### 3.3 A Runtime Directory

The runtime directory is the set of files that will be copied into the target game during installation.

In the current implementation, a usable runtime directory usually contains:

```text
runtime/unity_mono/
  AutoTranslator/
  ReiPatcher/
  Managed/
```

If your repository does not already include a ready-to-use `runtime/unity_mono`, you need to use the runtime-import step to extract it from a prepared source game directory.

### 3.4 Optional: Translation Service Configuration

If you want to use LLM translation or ordinary machine translation, you also need matching API settings such as:

- API Base
- API Key
- model name

After saving, these settings are written locally to:

```text
.private_translator/settings.json
```

This is local runtime data and should not be committed to the repository.

## 4. Install the Project

From the repository root:

```powershell
python -m pip install -e .
```

After installation, you can use:

```powershell
game-translator --help
```

Or directly:

```powershell
python main.py --help
```

## 5. Recommended Order of Operations

For a first run, it is best to follow this sequence:

1. Inspect the target game directory
2. Inspect the runtime directory
3. If the runtime does not exist yet, import the runtime first
4. Configure local translation settings
5. Perform a dry-run installation
6. If that looks correct, run the real installation
7. Start the local translation service
8. Only then launch the game

This makes troubleshooting much easier because you can see which step introduced the problem.

## 6. Command-Line Usage

## 6.1 Inspect a Game Directory

Use this to determine whether the target directory looks like a supported `Unity Mono` game:

```powershell
python main.py inspect-game "D:\Path\To\YourGame"
```

If detection succeeds, the output usually includes fields like:

- `game_dir`
- `exe_path`
- `data_dir`
- `managed_dir`
- `engine`
- `architecture`
- `is_unity_mono`

Common reasons for failure:

- the directory contains no `.exe`
- `*_Data` is missing
- `*_Data/Managed` is missing
- the target is not actually a `Unity Mono` game

## 6.2 Inspect a Runtime Directory

Use this to check whether the current `runtime_root` has the minimum required structure:

```powershell
python main.py inspect-runtime --runtime-root "D:\Path\To\runtime\unity_mono"
```

The current code focuses on these directories:

- `AutoTranslator/`
- `ReiPatcher/`
- `Managed/`

If any one of them is missing, runtime inspection fails.

## 6.3 Import a Runtime

If you already have a prepared source game directory, you can extract the needed runtime content into your own `runtime_root`:

```powershell
python main.py import-runtime `
  --source-game "D:\Path\To\SourceGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono"
```

This step does the following:

- resets the target `runtime_root`
- copies `AutoTranslator`
- copies `ReiPatcher`
- copies required `Managed` files
- copies `Translators`
- copies matching font files

Important notes:

- this is not an incremental merge
- the target runtime directory is reset before being rebuilt
- do not mix unrelated manual files into the same `runtime_root`

## 6.4 Dry-Run Installation

Before installing for real, run a dry run:

```powershell
python main.py install `
  --game "D:\Path\To\YourGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono" `
  --target-language zh `
  --dry-run
```

A dry run does not actually write files. Instead, it returns the planned operations, for example:

- copy `AutoTranslator`
- copy `ReiPatcher`
- copy `Managed`
- generate `AutoTranslator\Config.ini`
- generate `ReiPatcher/*.ini`

This is the safest way to confirm that your paths are correct before writing anything into the game directory.

## 6.5 Real Installation

Once the dry run looks correct, remove `--dry-run`:

```powershell
python main.py install `
  --game "D:\Path\To\YourGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono" `
  --target-language zh
```

During real installation, the tool writes or copies the relevant files into the target game directory.

It also writes an installation manifest in the game directory:

```text
.private_translator/install_manifest.json
```

This manifest is used later for uninstall and rollback.

## 6.6 Uninstall and Roll Back

If you want to remove the installed result, run:

```powershell
python main.py uninstall --game "D:\Path\To\YourGame"
```

The current implementation uses:

```text
.private_translator/install_manifest.json
```

to remove files written by the tool and restore backups where possible.

If the manifest is missing, uninstall capability is reduced.

## 7. GUI Usage

If you prefer a desktop interface, launch the GUI:

```powershell
python main_gui.py
```

Or:

```powershell
game-translator-gui
```

The GUI is more suitable when you:

- do not want to type commands manually
- want to save local translation settings
- prefer step-by-step button-driven actions
- want to inspect logs directly in the window

### 7.1 Recommended GUI Flow

Use this order:

1. Select the target game directory
2. Select the runtime directory
3. If needed, import the runtime from a prepared source directory
4. Select the target language
5. Configure the translation mode
6. Save translation settings
7. Start the local translation service
8. Run a dry-run install first
9. Then run the real installation
10. Finally launch the game

### 7.2 Translation Modes

The GUI currently supports two modes:

- `llm`
- `machine`

For `llm` mode, you usually need to provide:

- API Base
- API Key
- Model
- System Prompt

For `machine` mode, the current choices mainly revolve around:

- `deepl`
- `libretranslate`

### 7.3 What Happens When You Save Settings

When you click "Save Translation Settings", the program creates:

```text
.private_translator/settings.json
```

Later operations may also trigger silent saves, such as:

- starting the translation service
- installing
- testing translation

So this file is a normal runtime artifact, not an unusual side effect.

## 8. Local Translation Bridge Service

This project includes a local HTTP translation bridge service.

With default settings, it usually listens on an address like:

```text
http://127.0.0.1:14366/translate
```

Its role is to:

- receive text sent by the game runtime
- decide whether to use LLM mode or machine-translation mode
- return translated results
- write results into the local cache

## 9. Local Cache

Translation results are cached locally to reduce repeated requests.

The cache file is usually:

```text
.private_translator/translation_cache.json
```

If you later change:

- API Base
- model
- machine-translation provider

then old cache entries may no longer match the current translation backend exactly. That is expected.

## 10. Common Questions

### 10.1 Why Does `inspect-game` Fail

Check these first:

- did you select the real game root directory
- does the directory contain the main game `exe`
- does it contain `*_Data/Managed`

This project does not expect you to point directly at the `Game_Data` subdirectory. In most cases, you should choose the game root.

### 10.2 Why Does `inspect-runtime` Fail

Check these first:

- does `runtime_root/AutoTranslator` exist
- does `runtime_root/ReiPatcher` exist
- does `runtime_root/Managed` exist

### 10.3 Why Is `--dry-run` Recommended Before Installation

Because the most common problems are path mistakes, not core logic bugs:

- using `dist/PrivateGameTranslator` as if it were the game directory
- pointing to the wrong runtime directory
- trying to install into something that is not a `Unity Mono` game

`--dry-run` lets you see where the tool plans to write files before any actual write happens.

### 10.4 Why Does Uninstall Fail

Common reasons:

- `.private_translator/install_manifest.json` does not exist
- files were manually modified after installation
- the game directory was moved afterward

### 10.5 Why Should Local Settings and Cache Stay Out of the Repository

Because these files often contain:

- API configuration
- local runtime state
- cached translation results

They are not part of the source code itself, and they may include sensitive or temporary data.

## 11. Repository Publishing Advice

If you plan to maintain this as a public GitHub repository, the minimum good practice is:

1. publish source code, docs, and necessary scripts only
2. do not publish user-local settings or caches
3. do not publish packaged build artifacts by default
4. confirm redistribution rights for third-party runtime files separately
5. state clearly on the repository front page that the project currently supports `Unity Mono` only

## 12. Related Entry Points

- bilingual README overview: [`README.md`](../README.md)
- GUI launcher: [`main_gui.py`](../main_gui.py)
- CLI entry: [`main.py`](../main.py)
- CLI implementation: [`src/game_translator/cli.py`](../src/game_translator/cli.py)
- installer logic: [`src/game_translator/installer.py`](../src/game_translator/installer.py)
- runtime import logic: [`src/game_translator/runtime.py`](../src/game_translator/runtime.py)

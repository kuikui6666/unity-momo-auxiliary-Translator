# Private Game Translator

[中文](#中文说明) | [English](#english)

## 中文说明

一个面向 `Unity Mono` 游戏目录的本地翻译工具原型，使用 Python 实现。

当前版本主要提供：

- `Unity Mono` 游戏目录识别
- 运行时资源检查与导入
- 运行时安装与卸载回滚
- 本地 HTTP 翻译桥接服务
- 本地 JSON 翻译缓存
- 命令行入口
- `PySide6` 桌面界面

### 当前范围

- 只支持 `Unity Mono`
- 不支持 `Unity IL2CPP`
- 不支持其他游戏引擎
- 不定位为通用 OCR 或通用游戏翻译器

这个仓库更适合被理解为：

- `Unity Mono` 翻译运行时安装器原型
- 面向翻译流程的验证工具
- 桌面化封装示例

### 详细文档

- [中文手册入口](./docs/USAGE.md)
- [英文手册](./docs/USAGE.en.md)

### 仓库边界

本仓库主要公开的是源码和工具结构，不以打包分发第三方运行时为目标。

请先明确这些边界：

- 当前逻辑依赖 `*_Data/Managed`、`ReiPatcher`、`AutoTranslator` 这一路线
- 不适用于 `IL2CPP` 游戏
- 不适用于通用 Windows 游戏或任意文本来源
- 第三方运行时、字体、补丁工具是否可再分发，需要你自行确认许可证

### 当前能力

- 识别 `Unity Mono` 游戏目录结构
- 检查目标游戏目录和运行时目录
- 从已准备好的样例游戏目录导入运行时资源
- 为目标游戏生成 `AutoTranslator\Config.ini`
- 安装 `Managed` 补丁、配置文件和运行时目录
- 卸载并回滚由工具写入的内容
- 提供本地 HTTP 翻译桥接接口
- 支持大模型翻译模式和普通机翻模式
- 支持本地缓存，减少重复请求
- 提供 `PySide6` 图形界面封装常用操作

### 当前不包含

- 通用 IL2CPP 自动适配
- OCR 文本提取
- 在线配置向导
- 第三方运行时许可证整理
- 面向所有游戏类型的统一支持

### 安装

要求：

- Python `3.12+`
- Windows

安装：

```powershell
python -m pip install -e .
```

### 命令行示例

检查游戏目录：

```powershell
python main.py inspect-game "D:\Path\To\YourGame"
```

检查运行时目录：

```powershell
python main.py inspect-runtime --runtime-root "D:\Path\To\runtime\unity_mono"
```

导入运行时：

```powershell
python main.py import-runtime `
  --source-game "D:\Path\To\SourceGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono"
```

干运行安装：

```powershell
python main.py install `
  --game "D:\Path\To\YourGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono" `
  --target-language zh `
  --dry-run
```

卸载：

```powershell
python main.py uninstall --game "D:\Path\To\YourGame"
```

### 桌面界面

启动：

```powershell
python main_gui.py
```

或者：

```powershell
game-translator-gui
```

### 本地配置与缓存

工具运行时可能会生成：

- `.private_translator/settings.json`
- `.private_translator/translation_cache.json`

这些内容属于本地运行数据，不应提交到公开仓库。

### 打包桌面版

```powershell
powershell -ExecutionPolicy Bypass -File .\build_gui.ps1
```

默认输出：

```text
dist/PrivateGameTranslator/PrivateGameTranslator.exe
```

### 目录结构

```text
src/game_translator/
tests/
main.py
main_gui.py
build_gui.ps1
PrivateGameTranslator.spec
```

### 发布建议

如果你准备把它整理成公开仓库，建议后续继续做：

1. 补充 `LICENSE`
2. 明确第三方运行时的许可证边界
3. 把仓库名、包名、描述从 `private`/`MVP` 调整为公开版本
4. 尽量改成“用户自行提供第三方运行时”的流程
5. 补一个不含敏感信息的示例配置说明

### 免责声明

本项目用于本地化工作流研究、桌面工具封装和运行时安装流程验证。

在用于第三方游戏前，请你自行确认：

- 目标游戏的用户协议
- 第三方运行时或补丁工具的许可证
- 字体、DLL、配置模板等资源的再分发权限

## English

A Python-based translation-tool prototype for `Unity Mono` game directories.

The current version mainly provides:

- `Unity Mono` game directory detection
- runtime inspection and import
- runtime installation and uninstall rollback
- a local HTTP translation bridge
- local JSON translation cache
- a command-line interface
- a `PySide6` desktop UI

### Current Scope

- supports `Unity Mono` only
- does not support `Unity IL2CPP`
- does not support other game engines
- does not aim to be a universal OCR or universal game translator

This repository is best understood as:

- a `Unity Mono` translation-runtime installer prototype
- a localization workflow validation tool
- a desktop-wrapper example

### Documentation

- [Chinese usage entry](./docs/USAGE.md)
- [English usage guide](./docs/USAGE.en.md)

### Repository Boundaries

This repository mainly publishes source code and project structure. It is not intended to be a public redistribution bundle for third-party runtime binaries.

Please keep these boundaries in mind:

- the current workflow depends on the `*_Data/Managed`, `ReiPatcher`, and `AutoTranslator` route
- it does not apply to `IL2CPP` games
- it does not apply to generic Windows games or arbitrary text sources
- you should verify redistribution rights for third-party runtimes, fonts, and patch tools yourself

### Current Capabilities

- detect supported `Unity Mono` game directory structures
- inspect target game directories and runtime directories
- import runtime resources from a prepared source game directory
- generate `AutoTranslator\Config.ini` for the target game
- install `Managed` patches, config files, and runtime directories
- uninstall and roll back files written by the tool
- run a local HTTP translation bridge
- support both LLM mode and machine-translation mode
- cache translation results locally
- provide a `PySide6` desktop UI for common operations

### Not Included Yet

- generic IL2CPP support
- OCR-based text extraction
- an online setup wizard
- third-party runtime license packaging guidance
- a universal workflow for all game types

### Installation

Requirements:

- Python `3.12+`
- Windows

Install:

```powershell
python -m pip install -e .
```

### CLI Examples

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

### GUI

Launch:

```powershell
python main_gui.py
```

Or:

```powershell
game-translator-gui
```

### Local Settings and Cache

The tool may create:

- `.private_translator/settings.json`
- `.private_translator/translation_cache.json`

These files are local runtime data and should not be committed to a public repository.

### Packaging

```powershell
powershell -ExecutionPolicy Bypass -File .\build_gui.ps1
```

Default output:

```text
dist/PrivateGameTranslator/PrivateGameTranslator.exe
```

### Project Structure

```text
src/game_translator/
tests/
main.py
main_gui.py
build_gui.ps1
PrivateGameTranslator.spec
```

### Publishing Advice

If you want to refine this into a cleaner public repository, the next good steps are:

1. add a `LICENSE`
2. clarify redistribution boundaries for third-party runtime files
3. rename project/package metadata away from `private` and `MVP`
4. move toward a user-provided third-party runtime workflow
5. add sanitized example configuration guidance

### Disclaimer

This project is intended for localization workflow research, desktop tooling, and runtime-installation flow validation.

Before using it with third-party games, please verify:

- the game's user agreement
- the license of any patcher or runtime component
- redistribution rights for fonts, DLLs, config templates, and related assets

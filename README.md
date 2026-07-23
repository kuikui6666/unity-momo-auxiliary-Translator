# Private Game Translator

[中文](./README.md) | [English](./README.en.md)

一个面向 `Unity Mono` 游戏目录的本地化辅助工具原型，使用 Python 实现，提供：

- 当前版本只支持 `Unity Mono`
- 不支持 `Unity IL2CPP`
- 不支持其他游戏引擎或通用文本提取流程
- 命令行入口
- `PySide6` 桌面界面
- 运行时资源检查与导入
- 安装/卸载翻译运行时
- 本地翻译桥接服务
- 本地 JSON 翻译缓存

这个仓库当前更适合定位为：

- `Unity Mono` 游戏翻译运行时安装器原型
- 本地化工作流验证工具
- 桌面化封装示例

而不是“通用游戏汉化器”或“即开即用的第三方运行时分发仓库”。

详细使用说明请查看：

- [中文使用手册入口](./docs/USAGE.md)
- [English Usage Entry](./docs/USAGE.en.md)

## 仓库边界

本仓库主要公开的是源码和工具结构，不以打包分发第三方运行时为目标。

支持边界请先明确：

- 目前只支持 `Unity Mono`
- 当前逻辑依赖 `*_Data/Managed`、`ReiPatcher`、`AutoTranslator` 这一路线
- 不适用于 `IL2CPP` 游戏
- 不适用于通用 Windows 游戏、更不适用于所有文本来源

公开仓库使用时，建议按下面的边界理解：

- 源码可以保留在仓库中
- 用户本地配置、缓存、打包产物不应提交到仓库
- 第三方运行时、补丁工具、字体文件是否能再分发，需要你自行确认其许可证和使用条款
- 如果你准备做公开发布，建议把第三方依赖改成“由用户自行准备”

## 当前能力

- 识别 `Unity Mono` 游戏目录结构
- 检查目标游戏和运行时目录
- 从样例游戏目录导入运行时资源
- 为目标游戏生成 `AutoTranslator\Config.ini`
- 安装 `Managed` 补丁、配置文件和运行时目录
- 卸载并回滚由工具写入的内容
- 提供本地 HTTP 翻译桥接接口
- 支持大模型翻译模式和普通机翻模式
- 支持本地缓存，减少重复翻译请求
- 提供 `PySide6` 图形界面封装常用操作

## 当前不包含

- 通用 IL2CPP 自动适配
- OCR 文本提取
- 在线配置向导
- 第三方运行时许可证说明整理
- 面向所有游戏类型的统一支持

## 安装

要求：

- Python `3.12+`
- Windows 环境

安装依赖：

```powershell
python -m pip install -e .
```

## 命令行用法

检查游戏目录：

```powershell
python main.py inspect-game "D:\Path\To\YourGame"
```

检查运行时目录：

```powershell
python main.py inspect-runtime "D:\Path\To\runtime\unity_mono"
```

从样例目录导入运行时：

```powershell
python main.py import-runtime `
  --source-game "D:\Path\To\SourceGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono"
```

安装到目标游戏：

```powershell
python main.py install `
  --game "D:\Path\To\YourGame" `
  --runtime-root "D:\Path\To\runtime\unity_mono" `
  --target-language zh `
  --dry-run
```

卸载并回滚：

```powershell
python main.py uninstall --game "D:\Path\To\YourGame"
```

也可以使用安装后的命令入口：

```powershell
game-translator --help
```

## 桌面界面

启动桌面版：

```powershell
python main_gui.py
```

或者：

```powershell
game-translator-gui
```

桌面界面当前支持：

- 选择目标游戏目录
- 选择运行时目录
- 选择样例源目录
- 选择目标语言
- 配置大模型翻译参数
- 配置普通机翻参数
- 保存本地翻译配置
- 启动本地翻译桥接服务
- 检查游戏目录
- 检查运行时目录
- 导入运行时
- 干运行安装
- 正式安装
- 卸载回滚
- 查看日志输出

## 本地配置与缓存

工具运行时会在本地生成用户配置和缓存文件，例如：

- `.private_translator/settings.json`
- `.private_translator/translation_cache.json`

这些内容属于本地运行数据，不应提交到公开仓库。当前 `.gitignore` 已默认忽略这类文件。

## 打包桌面版

如果你要生成桌面可执行文件，可以执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_gui.ps1
```

默认输出位置：

```text
dist/PrivateGameTranslator/PrivateGameTranslator.exe
```

打包产物同样不建议提交到源码仓库。

## 目录结构

```text
src/game_translator/
  analyzer.py
  app_paths.py
  cache_store.py
  cli.py
  config_templates.py
  gui.py
  gui_launcher.py
  installer.py
  models.py
  runtime.py
  services.py
  settings_store.py
  translation_bridge.py
tests/
main.py
main_gui.py
build_gui.ps1
PrivateGameTranslator.spec
```

## 开发说明

如果你准备把这个项目整理成公开仓库，建议继续做这几件事：

1. 补充 `LICENSE`
2. 明确第三方运行时的许可证边界
3. 把仓库名、包名、项目描述从 `private`/`MVP` 调整为公开版本
4. 为第三方运行时改成“用户自行提供”的接入流程
5. 补一个不含敏感信息的示例配置说明

## 免责声明

本项目用于本地化工作流研究、桌面工具封装和运行时安装流程验证。

使用本工具处理第三方游戏时，请你自行确认：

- 目标游戏的用户协议
- 第三方运行时或补丁工具的许可证
- 字体、DLL、配置模板等资源的再分发权限

如果某些第三方组件不允许公开再分发，请不要把相关二进制文件一并发布到公开仓库。

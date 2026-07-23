from __future__ import annotations

import shutil
from pathlib import Path

from .models import RuntimeInfo


MANAGED_PATTERNS = (
    "ExIni.dll",
    "XUnity*.dll",
)


def inspect_runtime(runtime_root: Path) -> RuntimeInfo:
    # 一个“可安装”的运行时目录至少要同时具备这三块结构。
    runtime_root = runtime_root.resolve()
    auto_translator_dir = runtime_root / "AutoTranslator"
    rei_patcher_dir = runtime_root / "ReiPatcher"
    managed_root = runtime_root / "Managed"
    if not auto_translator_dir.exists():
        raise FileNotFoundError(f"运行时缺少 AutoTranslator: {auto_translator_dir}")
    if not rei_patcher_dir.exists():
        raise FileNotFoundError(f"运行时缺少 ReiPatcher: {rei_patcher_dir}")
    if not managed_root.exists():
        raise FileNotFoundError(f"运行时缺少 Managed: {managed_root}")

    managed_files = sorted(p for p in managed_root.rglob("*") if p.is_file())
    font_files = sorted(
        p
        for p in runtime_root.iterdir()
        if p.is_file() and (p.name.startswith("NotoSans") or p.suffix.lower() in {".ttf", ".otf"})
    )
    return RuntimeInfo(
        root=runtime_root,
        auto_translator_dir=auto_translator_dir,
        rei_patcher_dir=rei_patcher_dir,
        managed_files=managed_files,
        font_files=font_files,
    )


def import_runtime_from_game(source_game: Path, runtime_root: Path) -> RuntimeInfo:
    source_game = source_game.resolve()
    runtime_root = runtime_root.resolve()
    managed_source = _find_source_managed(source_game)
    auto_translator_source = source_game / "AutoTranslator"
    rei_patcher_source = source_game / "ReiPatcher"

    if not auto_translator_source.exists():
        raise FileNotFoundError(f"源游戏缺少 AutoTranslator: {auto_translator_source}")
    if not rei_patcher_source.exists():
        raise FileNotFoundError(f"源游戏缺少 ReiPatcher: {rei_patcher_source}")

    # 导入是“重建运行时目录”，不是增量同步，所以先清空目标目录。
    _reset_directory(runtime_root)
    (runtime_root / "Managed" / "Translators").mkdir(parents=True, exist_ok=True)

    shutil.copytree(auto_translator_source, runtime_root / "AutoTranslator", dirs_exist_ok=True)
    shutil.copytree(rei_patcher_source, runtime_root / "ReiPatcher", dirs_exist_ok=True)

    for pattern in MANAGED_PATTERNS:
        for file_path in managed_source.glob(pattern):
            target = runtime_root / "Managed" / file_path.name
            shutil.copy2(file_path, target)

    translators_dir = managed_source / "Translators"
    if translators_dir.exists():
        shutil.copytree(
            translators_dir,
            runtime_root / "Managed" / "Translators",
            dirs_exist_ok=True,
        )

    for candidate in source_game.iterdir():
        if candidate.is_file() and candidate.name.startswith("NotoSans"):
            shutil.copy2(candidate, runtime_root / candidate.name)

    return inspect_runtime(runtime_root)


def _find_source_managed(source_game: Path) -> Path:
    # 样例游戏里真正需要的托管补丁文件都来自 *_Data/Managed。
    for managed_dir in source_game.glob("*_Data/Managed"):
        if managed_dir.exists():
            return managed_dir
    raise FileNotFoundError(f"源游戏未找到 *_Data/Managed: {source_game}")


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
